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
  painting paragraph under Commenting from either view). Three more romp-only fields sit beside
  `anchorAt` since the tie-break (2026-09-11, decision 51): `ordinal: <number>` and `copies: <number>`,
  the copy's 1-based index among the whole anchor's matches and their count at the moment of the write,
  and `section: <string>`, the heading path above the passage in a markdown file (the nearest preceding
  headings from the top level down, each heading's text cut at 200 characters, `SECTION_HEADING_CAP`,
  joined with " > "; empty for a file without headings or a non-markdown file, the file's kind judged
  from its name, `.md` or `.markdown`, never from the sidecar's own `path` field). The host writes them
  at creation (none for a passage whole at more places than the refresh enumerates, where no count is
  known; the review's third round, 2026-09-11) and refreshes them with the position on every
  sidecar write for a comment whose position names its copy, and reads them when the whole anchor ties
  and the position names none of the copies, not even by the quote with one side of its context whole
  beside it (such a position, the other side edited, names the passage, and the copies whole elsewhere
  are the other copies; the same round, and the review's fourth, which asks for the one side: a bare
  occurrence of the quoted words is a stale position like any other): the ordinal's copy while the count of copies is unchanged, unless the stored
  heading path names other copies and not the ordinal's, when the two fields disagree and the tie is a
  guess (the same round; decision 51 says why); else, the count changed, the one copy under the stored
  heading path; confirmed either way; else the nearest copy to the position, a guess. Every reply
  carries the verdicts (`placed`, per comment id), except that while every change to the text is on
  record a verdict the recorded changes carry to another place is left to the next write's refresh (the
  same round), and the panel paints a confirmed copy plainly. The other editors and the CLIs write the
  whole object back, so the six fields survive them.
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
scoring) is charged at its own cost to one budget per write (`REFRESH_SCAN_BUDGET`); a passage
still at its position costs no scan to place, only the one classification pass per distinct anchor
that stamping its copy fields takes on every write since the tie-break (below; before it such a
passage cost nothing), and past the budget the remaining comments keep their position and stderr
says how many, once per write, and a comment whose stamp the budget refuses keeps the fields it
has, or none, and stderr says how many of those, once per write; and a stored comment's anchor is
located with its `anchorAt` as the hint. The comments without the fields are stamped before the
rest, so a sidecar with more distinct anchors than one write scans gains fields where it has none
before it refreshes the fields it has (`noteUnstamped` is the note; the review's first round,
2026-09-11: before it the skip was silent, and a comment past the budget never gained the fields). Every
reader of a stored anchor in the host (the figure a passage names, a re-place, the reply's `placed`)
goes through `locateStored` since the tie-break (2026-09-11,
decision 51): the position first, where the whole anchor still sits at it, and where the quote sits at it
with one side of its context whole beside it while the whole anchor sits elsewhere (`quoteSitsAt`: the
passage whose surroundings on the other side were edited, the state the refresh leaves when a recorded
change edited the chosen copy's context and not its text; the copies whole elsewhere are then the other
copies, no rule below places the comment on one, and the reply's map carries no verdict for it, so the
panel paints by its own engine, the nearest whole copy as a guess with its cue, or, with exactly two
copies, the one still whole, plainly, as since the anchors follow-on; the review's third round,
2026-09-11, which took the quote alone, and its fourth, which asks for the one side, since a bare
occurrence of the quoted words is what a stale position lands on by a coincidence of distance);
then, when the whole anchor sits at several places and the position names none, the copy fields,
`ordinal` while `copies` equals the count of matches now, unless the stored `section` names other
matches and not the ordinal's, when the two fields disagree and neither confirms (the same round); else,
the count changed, the one match under the stored `section`; both confirmed; else the match
nearest the position, a guess, and a tie with no position refuses `anchor-ambiguous` as before; an
anchor whole nowhere is the engine's. The reply's map (`placedFor`) carries the verdict of every such
tie, except that while every change to the text is on record (the text as the sidecar's last writer left
it) a verdict the recorded changes carry to another copy, or to the quote's own occurrence, is dropped
for the next write's refresh to settle (`carriedTo`; the same round: before it a status between a
tracked edit inside the first of two copies under one heading and the next host write confirmed the
second copy by section, from a position the recorded edit accounted for); the walk over the copies the
recorded changes can have carried a position to (`reachable`, the refresh's and the map's) reads the
changes off one sorted index and is charged to the same budget, and a comment whose walk does not fit
is one the changes say nothing about, its position kept and counted by the refresh, its verdict
forwarded by the map (the fourth round: uncharged, the walk held a status on ten thousand pending
changes past the deadline). The refresh stamps the three
fields on every comment whose position names its copy once its pass is done (`stampCopy`), under the
same budget, and the decisions' self-check carves them out with `anchorAt`. Creation stamps them alone
where the whole anchor is at no more places than the refresh enumerates (`REFRESH_COPIES_MAX`): past
that no count is known and none is written, as the stamping pass already refused to (the same round;
before it the cap itself was written as the count). Reject writes the sidecar first, then the
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
Two later changes narrow that list of refusals: Slice 8 of plans/markdown-viewer.md positions a
table's cells and a code block's lines as prose, so a selection inside one maps, and decision 53
(2026-09-18) lets a selection across several cells of one table anchor to its span, the pipes, the
delimiter row and the line feeds between the cells inside the quote as a Raw selection over the same
characters mints them; and decision 52 (2026-09-18) renders an inline start tag with no end tag in
its block as its own characters on both sides, so the paragraph holding one maps where it used to
open an element the pairing did not model and refuse every block after it.

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
review, 2026-09-07; before it the guess was painted as located; with exactly two copies the one still whole is
the engine's one best hit, not a tie, and is painted plainly, on the copy the person did not comment: the host
paragraph and decision 51 say so and why). Since the tie-break (2026-09-11,
decision 51) the status carries the host's verdict for every such comment (`placed`): a copy the host
confirmed from the fields stored with the comment (the ordinal's copy while the count of copies is
unchanged, unless the stored heading path names other copies and not that one; else, the count changed,
the one copy under the stored heading path; decision 51 has the rules) is the painter's hint in place of
the stale position (`placedAt`), so it is painted as the chosen one, with no dashed ring and no tag; a
guessed verdict, or none (a tie whose verdict the recorded changes carry elsewhere has none until the
next write settles it, and a position the quote sits at with one side of its context whole beside it
has none, the panel painting that comment by its own engine as before the tie-break; the review's third
round, 2026-09-11, and its fourth), paints as before, and the card's words end by saying how to confirm the copy. A passage comment's guessed
copy has its card offer the Reveal those words name (the review's first round, 2026-09-11; before it the card
offered Reveal only for a passage it could not paint, and named a button it did not have): it switches to Raw and
scrolls to the guessed copy, and its title says that a comment saved from the copy you mean is placed on that copy
and this one keeps its tag until you resolve it. A confirmed place the view's text has moved past (the poll's reload paints
before the fresh status lands; a refused refresh keeps the old status) paints the copy nearest that place as a
guess whose words name the confirmed place (`confirmedAt`), never plainly on a copy the host did not vouch for
in the text shown.
A region comment on an embed line that recurs is in the same state, its rectangle on the figure nearest
the hint; its words end with the recourse a region has, a new region drawn on the figure meant, with a
mouse (Reveal for a region scrolls to its picture, never to Raw, and Re-place keeps the anchor and its
fields), and its card offers no Reveal (the review's second round, 2026-09-11).
Those are the words of a view that paints the copy: with the editor up (Slice 5) no highlight of ours is
painted and the card offers neither Reveal nor the composer, so a guessed card's words say only that the
copy is a guess and name the way there first, leave edit mode, then reveal it and save again from the
right copy (`UNSURE_IN_EDITOR`, `PASSAGE_CONFIRM_AFTER_EDIT`; a region's, leave edit mode, then draw a
new region in the view that shows the image, `REGION_CONFIRM_AFTER_EDIT`), a passage's save line
standing under them as in the read view; a region whose picture the view does not show (Raw) is told
which view has it (`REGION_CONFIRM_UNSEEN`); and a pictured region's card on a coarse pointer, which
offers no Re-place, ends with the pictured view's words less the sentence about Re-place
(`REGION_CONFIRM_TOUCH`). Before it the card in the editor named a Reveal and a save it did not offer,
the Raw card said to draw on a figure the view did not show, and the phone's card named a Re-place it
did not have (the review's third round, 2026-09-11, and the sweep after it).
The stored position is an offset
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
A highlight or a change mark over an anchor that spans several cells of a table is one mark per cell
over the cell's own text, none over the pipes between them (decision 53: the exact path's
`wrapBetween` gathers the highlight units between the two ends and `wrapRuns` skips the
whitespace-only text between the cells' boxes), and one over an inline tag rendered as
literal text wraps the tag's characters (decision 52).

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
- Rendered: a selection touching code, a table, an HTML block, an entity-bearing paragraph, or an
  escaped link label is refused, the comment survives, and the Raw offer opens with the passage
  selected when its text occurs in the source, else scrolled to the block. Since Slice 8 of
  plans/markdown-viewer.md and decision 53 the code and the table are no longer refusals: a code
  line, a cell and a selection across several cells of one table map (their own criteria stand in
  that plan's Slice 8 note and in decision 53); the HTML block, the entity-bearing paragraph and the
  escaped label refuse as stated.
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
too, where the tint came through the text-match fallback until Slice 8 of plans/markdown-viewer.md
positioned the cells and the lines, so a substitution there is shown; a deletion at the same offset
was card-only and places in the fence's line and in the cell since that slice. A point at the edge of
a painter's own mark (a change's
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
budget per write, and a passage still at its position costs none to place, one classification pass per
distinct anchor for its copy fields on every write since the tie-break (below). The panel passes a card's `anchorAt` to the
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
outcomes against the panel and the host. The tie-break (2026-09-11, decision 51) closes the case the
refresh leaves open: after an edit nobody recorded, the position names no copy and the changes vouch
for nothing, so the copy nearest the stale position was painted as a guess for good. The host now
writes `ordinal`, `copies` and `section` beside the position (`stampCopy`, at creation and with every
refresh) and breaks the tie by them (`locateStored`, the one reader of a stored anchor): the ordinal's
copy while the count of copies is unchanged, confirmed, unless the stored heading path names other
copies and not the ordinal's, when the two fields disagree and the tie is a guess (the review's third
round, 2026-09-11); else, the count changed, the one copy under the stored heading path,
confirmed; else the nearest, a guess, whose words on the card end with "Reveal it and save again from
the right copy to confirm." and whose card offers that Reveal (the review's first round, 2026-09-11).
That is a passage comment's card: a region comment whose embed line ties is guessed by the same rules,
and since Reveal for a region scrolls to its picture, never to Raw, and Re-place keeps the anchor, its
position and its fields, its words end with the recourse a region has, a new region drawn on the figure
meant, with a mouse, and its card offers no Reveal (the review's second round, 2026-09-11; decision 51
says why). Both are the read view's card: with the editor up the words say only that the copy is a
guess and name the way there first, leave edit mode, then reveal it and save again from the right copy
(a region's: then draw a new region in the view that shows the image), and the card offers no Reveal; in
Raw a region's words name the view that shows its picture, and on a coarse pointer they leave out the
sentence about the Re-place the card lacks (the review's third round, 2026-09-11, and the sweep after
it). A position the quote sits at with one side of its context whole beside it, the other side edited,
names the passage before any rule runs, and the copies whole elsewhere are the other copies, never placed
on (the same round, whose test took the quote alone, and the review's fourth, which asks for the one side;
before the third a tracked edit inside one of two copies under one heading had the section rule confirm
the other).
Tests: `tools/file-comments-host-tiebreak.test.mjs` (the section helper,
creation, the refresh, the rules in order, a read that rewrites nothing, the decisions' carve-out),
`ui/webview/file-comments-tiebreak.test.ts` (the confirmed and the guessed paint),
`ui/webview/file-comments-tiebreak-browser.test.ts` (Chromium and Firefox, Rendered and Raw: a raw
insertion above, the status refreshed, the highlight on the right copy with no tag) and
`tools/file-review-plan-tiebreak.test.mjs`, which pins this note, decision 51, the contract, the ADR
and the guide against the host, the panel and the model; and from the review's first round (2026-09-11)
`tools/file-comments-host-tiebreak-review.test.mjs`, `ui/webview/file-comments-tiebreak-recourse.test.ts`,
`tests/test_guide_files_comments_confirm.py` and `tools/file-review-plan-tiebreak-review.test.mjs`, and from
its second `tools/file-comments-host-tiebreak-review-2.test.mjs`, `ui/webview/file-comments-tiebreak-region.test.ts`,
`tools/file-review-plan-tiebreak-review-2.test.mjs` and `tools/file-review-plan-tiebreak-review-3.test.mjs`, and from
its third `tools/file-comments-host-tiebreak-review-3.test.mjs`, `ui/webview/file-comments-host-tiebreak-review-3-panel.test.ts`,
`ui/webview/file-comments-tiebreak-shown.test.ts`, `ui/webview/file-comments-tiebreak-touch.test.ts` and
`tools/file-review-plan-tiebreak-review-4.test.mjs` (the Tests section says what each drives).

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
  stale copy, the lock the concurrent writer.
  Residual (decision 49): a lock names its writer's pid namespace only when that is not the initial one, and a pid is
  judged only from the namespace that stamped it, so the lock serializes the writers of one machine; a lock written
  from another machine over a shared filesystem is judged as if its pid were this machine's, dead when no process here
  has the number, else by its stamp's age.
  The Obsidian
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
  modules that drive the painted states against the tree. `tools/file-review-plan-tiebreak.test.mjs` pins
  decision 51 and the tie-break's sentences here against the host (`locateStored`, `stampCopy`, the
  fields), the panel (`placedAt`, the words), the model, the ADR's six fields and the guide's sentence,
  and the tie-break modules against the tree. `tools/file-review-plan-tiebreak-review.test.mjs` holds the
  tie-break review's two corrections to the record against the host: a passage still at its position costs
  its copy fields one classification pass per distinct anchor on every write, charged to the budget, and
  past it keeps the fields it has while stderr says how many, once per write (the stamping pass of
  `refreshAnchorAts`, `noteUnstamped`, `fullMatches`'s memo), and a tie with no position is settled by the
  fields before it is refused (`locateStored`). From that review's first round (2026-09-11):
  `tools/file-comments-host-tiebreak-review.test.mjs` drives the real host as a child process over the round's
  findings on it: the heading path read as the viewer renders the file (CRLF line ends, a leading BOM, a
  front-matter block by the viewer's own test, each heading's text cut at `SECTION_HEADING_CAP`), the file's
  kind judged from its name and never the sidecar's `path` field, the nearest fallback read off the enumerated
  matches (a status over hundreds of stale tied comments inside the kernel's deadline), the stamping pass's
  order and its stderr note, the engine-placed 1-of-1 stamp and `placed` on every write verb's reply;
  `ui/webview/file-comments-tiebreak-recourse.test.ts` drives the panel over the tie-break stand-in: a guessed
  copy's card offers the Reveal its words name, a confirmed copy's and a unique passage's offer none, and a
  confirmed place the view's text moved past paints the nearest copy as a guess whose words name that place,
  through the poll's path to that state; and `tests/test_guide_files_comments_confirm.py` holds the guide's
  sentence on saving again (a new card on the right copy, the old one keeping its tag until resolved) to the
  panel and walks it on the real host. From its second round, `tools/file-review-plan-tiebreak-review-2.test.mjs`
  holds the record's account of the first round to the code: the stamp's note (`noteUnstamped`), the tied
  CLI comment no host write stamps while its tie holds (`refreshAnchorAts`, on the real host), the heading
  cap and the file's kind from its name, the guessed card's Reveal and the confirmed place the view moved
  past, the guide's sentences in the Docs section, and the first round's modules against the tree.
  From the same round, `tools/file-comments-host-tiebreak-review-2.test.mjs` drives the real host as a child
  process, or its exported helpers, over the round's findings on the host: a scan the budget cut serves no
  caller without a budget (`fullMatches`, so `passageFigure` and `doRetarget` read no null from
  `locateStored`), the heading and front-matter regexes take a whitespace run without quadratic backtracking,
  a whole-nowhere anchor under a budget is answered unplaced after the classification pass alone (`placedFor`
  spends nothing on a verdict it drops), the refresh returns before judging a null store, `stampCopy` keeps
  the fields of a comment carried to the quote's other occurrence, and `markdownOf` leaves an unjudged store's
  heading path as it is, with its note once per process. `ui/webview/file-comments-tiebreak-region.test.ts`
  drives both card kinds over the rendered stand-in and a Raw body: a region on the second of two embeds whose
  title an unrecorded write edited has its rectangle on the guessed figure and the tag, its words end with the
  region's recourse (a new region, with a mouse; what Re-place does instead), and its card offers Reply,
  Resolve and Re-place on a pointer that draws, Reply and Resolve on a coarse one, and no Reveal in either
  view; a passage comment on the same line, guessed, carries the words that ask for the save and a line under
  them saying what the save does (the Reveal's title ends with the same words, and Reveal switches to Raw at
  the guessed copy), and a passage whose position names its copy carries neither. On the coarse pointer the
  words are the pictured view's less the sentence about the Re-place the card lacks (`REGION_CONFIRM_TOUCH`,
  mirrored from the panel as `REGION_CONFIRM` is; the sweep after the third round, 2026-09-11).
  `tools/file-review-plan-tiebreak-review-3.test.mjs` holds the record's account of the second round (the
  region card's words and its missing Reveal, the passage card's line, the round's modules) to the panel
  (`copyUnsureWords`, `REGION_CONFIRM`, `renderCard`, `reveal`), the host (`doRetarget`) and the tree. The
  third round wrote it for the second's account; its own account is held below. From that third round
  (2026-09-11), `tools/file-comments-host-tiebreak-review-3.test.mjs` drives the real host as a child process, or
  its exported readers, over the round's findings on the host: a comment the refresh carried to the quote's own
  occurrence, one side of its context still beside it, answers the position and the reply carries no verdict
  for it (`locateStored`, `quoteSitsAt`, `placedFor`); a verdict the recorded changes carry elsewhere is dropped while every change is on record and
  one they carry to the same copy stands (`carriedTo`); the ordinal yields to a stored heading path that names
  other copies and not its own, while a heading renamed or deleted above the copies leaves it confirmed;
  creation writes no copy fields for a passage whole at more places than `REFRESH_COPIES_MAX`, and a later
  write adds none; a front-matter block closes on `---` alone, so a heading in a block closed only by `...` is
  the passage's path; and a status on `REFRESH_COPIES_MAX` copies with two thousand tied comments answers
  inside the kernel's deadline (`copiesUnder`, `nearestOf`). `ui/webview/file-comments-host-tiebreak-review-3-panel.test.ts`
  drives the panel's half of that state, over the tie-break stand-in and over the real host's reply: with no entry
  the panel paints the nearest whole copy in the dashed cue with the stored position's words and nothing at the
  quote, after a tracked edit inside the chosen copy's context and after a raw edit of the surroundings alone,
  and an entry the host declines to forward would close nothing, since the panel paints no confirmed copy from
  an offset the whole anchor is not at. `ui/webview/file-comments-tiebreak-shown.test.ts`
  drives the words for what the render shows, over the recourse module's stand-in with a viewer that flips
  into edit mode as `enterEdit` does: with the editor up a guessed passage card names the way there (leave
  edit mode, then reveal it and save again) and offers no Reveal, the save's line under the words, and the
  read view's words and Reveal return when the edit ends; a comment with no verdict, one whose confirmed
  place the view moved past and one with no position wear the same words while editing, and each its own
  after; a confirmed copy and a unique passage carry no tag and no note in the editor; and in Raw a region
  on the second of two embeds after an unrecorded title edit has the embed line as its guess and words that
  name the view showing the image, not a figure Raw lacks or the Re-place it does not offer, the editor's
  words naming the way there first. `ui/webview/file-comments-tiebreak-touch.test.ts` drives the same region
  on a coarse pointer with the picture in view: the words leave out the sentence about the Re-place the card
  lacks and end with what drawing takes, the fine pointer's card names the Re-place it offers, word for
  word, Raw's words are the same on either pointer, and the words name Re-place exactly when the card has
  the button. `tools/file-review-plan-tiebreak-review-4.test.mjs` holds the record's account of the third
  round (decision 51, the contract, the host and painting paragraphs, the note) to the host
  (`locateStored`'s order with the position the quote names with one side of its context and the yield,
  `placedFor`'s recorded window and the budgeted walk, `buildComment`'s cap, the front-matter reader), the
  panel (`copyUnsureWords` and its words) and the tree, and drives the yield and that position on synthetic
  markdown.
  `tools/file-review-plan-attribution.test.mjs` holds the margin-layout note to the
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
  substitution inside a code fence or a table cell gets its point before its tint and is reported
  painted while a deletion at the same offset places in the fence's line and in the cell (card-only
  before Slice 8 of plans/markdown-viewer.md positioned them);
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
  by heredoc (`bash <<EOF`, `bash -s`, `sh -`) read like `sh -c`, and since the fifth addendum's second fix-up
  (2026-09-20) one fed by a literal echo or printf piped into it; `-c` in an option cluster (`bash -lc`,
  `sh -ec`); python and node options before a heredoc on stdin; a prefix with options (`sudo -u`, `env -u`,
  `timeout -s`, `exec -a`); pushd moving the cwd and popd leaving it unknown; `[[ a > b ]]` and `(( a > b ))`
  comparing in bash and zsh and, since round 5's fifth addendum (2026-09-20), read in dash's grammar too, a
  tracked target there refusing, an operator glued to the closing `]]` and a process substitution among the
    operands read as anywhere (the addendum's fix-up), while `[ a > b ]` redirects in every shell; a function body moving nothing after it; `Path(x).open('w')`, `open()`
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
  re-read and one retry with the fresh fence, the success applied as the status; no retry on a second `busy`, the
  refusal handed to the viewer with its code and the host's words; no retry either when the re-read shows other
  records, the refusal handed on under the same code with the head's row's words, `MOVED_UNDER_EDIT`,
  `CHANGES_MOVED_UNDER_EDIT` or `CHANGES_UNREAD_UNDER_EDIT`, since a retry could only refuse);
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
  The third round's own commit showed the scan's other side (found in the fourth round, 2026-09-11): it added three
  modules for the lock's own `store-io.mjs` behaviours that cite decision 49 and this plan, which the scan reached and
  this bullet did not name, so the inventory pin was red at that commit, and two more the scan cannot reach, one
  citing the decision without the plan's name and one citing the lock and no decision. All five are named here:
  `tools/store-io-lock-inode-reuse.test.mjs` (the entry judged stale, lock or claim, kept open from the judgment
  through its unlink, so the filesystem's reuse of a freed inode number cannot hand a waiter's fresh lock the judged
  number and a breaker suspended past the bound cannot remove it: one interleaving driven by hand in-process, and a
  breaker child stalled at its look for the unlink while a real writer breaks its claim and the dead lock and writes,
  the breaker waiting for that write instead of entering beside it); `tools/store-io-lock-folder-name.test.mjs` (an
  entry at `.trackchanges`'s name that is not a directory refused at once, held false and naming it: a link to nothing
  left alone with nothing created, a regular file refused with the OS error, a link to a directory followed with the
  folder behind it kept, and the real `track-comment` on such a root printing the line and exiting 1 in well under the
  wait, where before it spun the whole wait and reported a live writer); `tools/store-io-lock-pid-namespace.test.mjs`
  (a pid judged only by a reader in the namespace that stamped it: in a child namespace an initial-namespace writer's
  dead pid's fresh lock is left alone and the writer waits the bound out and refuses as held, a stamp past the bound
  is still broken, and in the initial namespace a dead pid's lock is broken at once; a writer in a child namespace
  stamps `pid ts` and then `ns <inode>`, one in the initial namespace `pid ts` alone; a child-namespace writer's live
  lock whose pid is a free number outside is left alone by a writer in the initial namespace, which waits the bound
  out, where before it was broken at once; the same lock read from the stamping namespace is broken at once when the
  pid is dead there and read from a third namespace waited out; each case a child process with the namespace read
  through a stand-in, plus this machine's own namespace with none, and a real child namespace where `unshare` can make
  one unprivileged, the vendored `track-comment` there refusing a live lock held outside it and a holder inside
  stamping the namespace a writer outside waits behind, skipped where it cannot);
  `tools/README-track-changents-patch-0008-row.test.mjs` (the vendored README's row for patch 0008 held to
  `store-io.mjs`'s constants as the ADR bullet is: both names and the line in the row and no third, the row's account
  of the folder against store-io's make and remove sites, and the row, the patch header and the ADR bullet listing one
  set of names); `ui/webview/file-comments-busy-retry-fence.test.ts` (the retry after `busy` as it runs: the re-read
  after a refusal for a lock still held shows the same clocks and the retry goes out on the same fence, the holder's
  rename landing under it refuses `store-moved`, which reaches the viewer with its code and the host's words with no
  third save; the contrast where the holder finished before the re-read; and the panel's comments at `MOVED` and on
  `saveThroughComments` held to what the code gives). `tools/file-review-plan-sidecar-lock-modules.test.mjs` holds
  those five by name, whatever they cite (every `tools/store-io-lock-*` and `tools/README-track-changents-patch-*`
  module in the tree, and the fence module), to this bullet and to decision 49, what this bullet says of each to that
  module's cases, and decision 49's pid-namespace sentences (a pid judged only by a reader in the namespace that
  stamped it, named on the stamp's second line from any but the initial one; a stamp more than 15 s from the reader's
  clock either way a dead writer's) to `store-io.mjs`. The fourth round's own modules:
  `tools/store-io-lock-clock.test.mjs` (a stamp more than the bound ahead of the reader's clock is a dead writer's
  too: a lock stamped `1 <an hour ahead>` broken at once, pid 1 alive to every reader or not, a live pid's lock an
  hour ahead the same and five seconds ahead waited behind, a stampless lock's mtime judged the same way, a dead
  breaker's claim an hour ahead removed and the break proceeding, and the real `track-comment` against such a lock
  landing its comment in well under the wait, where before a lock committed or planted with a future stamp held every
  write to `busy` with no message naming it); `tools/file-comments-host-decision-lock.test.mjs` (the decision verbs
  load under the lock: against a writer that holds `<sidecar>.lock` and saves a comment 300 ms later, a reject-all, an
  accept by id and a save with a rejection from the editor each answer after that save, refuse `store-moved` on the
  moved fence, and the retry lands both the comment and the decision; and the source, `loadForDecision` called only
  inside the function `underStoreLock` runs); `tools/track-comment-race-vocabulary.test.mjs` (the race module held to
  the glossary's word for a comment with its replies, the vendored `track-reply`'s own flag and line excepted, and its
  replies case described in the same words as this bullet);
  `ui/webview/file-comments-changes-review2-busy-prose.test.ts` (the changes suite's explanation of its `busy` case
  held to the premise the fence module pins in the panel's source, the retracted sentence banned there too). The last
  two cite no decision, so the scan does not reach them; they are named here by hand.
- The inline tag and the cells (2026-09-18, decisions 52 and 53): `ui/webview/md-literal-tags.test.ts` (the
  literal-tags rule at the token level, the escape against marked's own, the source pins over both callers and over
  md-config.ts and the chat's modules); `ui/webview/anchor-map-literal-tags.test.ts` (the map over a DOM stand-in of
  the quirks-mode parse, two FAILS-BEFORE cases, the contract's shapes);
  `ui/webview/anchor-map-literal-tags-browser.test.ts` (the real pane in Chromium);
  `ui/webview/anchor-map-cells.test.ts`, `ui/webview/anchor-map-cells-formulas.test.ts` and
  `ui/webview/anchor-map-cells-browser.test.ts` (a selection across cells anchors, its quote and range equal to the
  Raw path's, the paint one mark per cell, a FAILS-BEFORE case on two body cells, the formula-only and picture-only
  cell shapes, a real drag saved through the panel); `tests/test_guide_files_cells_and_code_lines.py` (the guide's
  sentences and the retired one-cell machinery at the source). `tools/file-review-plan-inlinetag.test.mjs` pins
  decisions 52 and 53 here against the module (`literalizeUnclosedTags`, `VOID_ELEMENTS`), both callers (mdBlock's
  three steps, `placeTokens`' lex line, one void list), the retired one-cell machinery and the anchor line in
  anchor-map.ts, the guide's sentences, plans/markdown-viewer.md's two pointer sentences, this bullet's modules
  against the tree, and `tools/file-review-plan-about.test.mjs`'s DECISIONS_END;
  `tools/file-review-plan-inlinetag-rawblock.test.mjs` runs marked over a document with an unclosed `<kbd>`,
  `<pre>`, `<code>` or `<script>` and holds decision 52's scope sentence to the lexer (every later block unescaped
  until an end tag of any of the four names or the document's end, `inLink` the same); its lexer legs skip where
  marked is not installed, which is every run of CI's shell job, so
  `ui/webview/file-review-plan-inlinetag-rawblock.test.ts` (the second round) holds the same scope through both
  callers' lexes (mdBlock's marked.lexer over a copy of the defaults, `placeTokens`' `Lexer.lex`) under the one
  configuration, built and run by the extension job's `npm test`, and the tools module holds that twin and its
  runner to the tree. The first round's other three modules (2026-09-18), found unrecorded in the second round and
  named here since:
  `ui/webview/md-literal-tags-tag-syntax.test.ts` (the self-closing flag read as the HTML tokenizer reads a tag,
  the `image` alias left HTML, the stacks per name against the one list as an oracle and their linear time);
  `tests/test_guide_files_own_html_foreign_tag.py` (the guide's qualification for a child tag left open inside an
  inline `svg` or `math`, each clause held to the code); `tools/markdown-viewer-plan-decision52-pointers.test.mjs`
  (the four in-place pointers at decision 52 in the Slice 5 section of plans/markdown-viewer.md).
  `tools/guide-own-html-block-tag.test.mjs` (the second round: where the guide says the rule stops, a tag first on
  its line that markdown reads as an HTML block, each clause held to the installed marked's block html rule, to the
  rule's walk, which reads inline runs alone, and to the map's refusal of an html block; since the review of the
  slice's PR, round 1, the guide's sentence on the tags that take the rest of the file when they stay HTML, at the
  lexer). `ui/webview/guide-own-html-block-tag.test.ts` (the same round: that module's lexer legs, the loss
  sentence's included, through both callers' lexes under the viewer's configuration, run by the extension job's
  `npm test` where the tools module's lexer legs skip).
  `tools/file-review-plan-inlinetag-records.test.mjs` holds decision 52's account of the first round to the code
  (the stacks per name, `IMG_ALIAS`, `isSelfClosingTag`, the `open` array and the self-closing spelling's wrapper,
  the fragment target a converted tag loses, the math breakout class) and this bullet's inventory to the tree
  both ways: every module it names is in the tree, and every test module under `tools/`, `ui/webview/` or `tests/`
  that cites decision 52 or 53 is named here or in one of the two records, so a later round's module cannot land
  unrecorded. Since the review of the slice's PR (round 1, 2026-09-19) mdBlock's three steps are one exported
  function, `viewerHtml` in file-view.ts, which mdBlock calls with the walk it ran before, and
  `tools/file-review-viewer-recipe.test.mjs` holds that function to the source (its five statements in order,
  mdBlock's call and walk) and holds every test module under `ui/webview/` that stands a Rendered body in for the
  viewer's to it by grep: none calls marked's parser itself, none fills a node stand-in from `marked.parse` alone
  but the one contrast `ui/webview/anchor-map-cells-formulas.test.ts` draws with the tree the viewer built before
  the rule, and every module that calls `viewerHtml` imports it from file-view.ts.

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
25); `docs/install.md` names the Bash-side guard beside the vendored one. With the tie-break (2026-09-11), that a
comment on text which occurs more than once is placed again by its own record of where it was, which copy it is and
the heading above it when the file has changed around that occurrence, that when none of those can tell the copy
shown is a guess and the card says so, and that saving the comment again from the right copy adds a new card on that
copy with no tag while the old card keeps its tag until you resolve it (the review's first round reworded that last
sentence, which had promised a confirmation of the same comment that no verb performs;
`tests/test_guide_files_comments_anchors.py` holds the first two to the panel and the ADR,
`tests/test_guide_files_comments_confirm.py` the last to the panel and the real host).
With decisions 52 and 53 (2026-09-18), that a table cell, a selection across several cells of a table and a line of a
code block can be commented from the Rendered view like any passage, that a comment across cells quotes the pipes
between them as the file holds them, and that a formula is what cannot be mapped from the Rendered view
(`tests/test_guide_files_cells_and_code_lines.py` holds the sentences to the map's source), and, in the paragraph on a
file's own HTML, that a tag opened in a line of prose and not closed in the same block is shown as the characters
typed rather than read as HTML, a tag closed in the same block, a void tag and a tag written with a slash before its
`>` (`<x/>`) staying HTML, a chat message not read this way (`tools/file-review-plan-inlinetag.test.mjs` holds the
sentence to the guide and the module), that a tag first on its line, which markdown reads as an HTML block, is HTML
as before, the same placeholder included, and that a `<title>`, `<script>`, `<style>` or `<iframe>` that stays HTML,
written with the slash mid-sentence or first on its line, takes everything after it out of the Rendered view up to
an end tag of its name or the end of the file, a `<textarea>` so placed showing that stretch as unformatted
characters, the file's own text after the tag first on its line and the HTML the viewer built from the rest after the
tag written with the slash, its tags among the characters (`tools/guide-own-html-block-tag.test.mjs` holds those
clauses to the guide, the installed marked's lexer and the map, `ui/webview/guide-own-html-block-tag.test.ts` the
lexer legs under the viewer's configuration in CI, and `tests/test_guide_files_own_html_foreign_tag.py` the
paragraph's sentences in their order and the rule's two exclusions at the source).
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
    path the kernel opens, so a symlink to a tracked file carries no write past it (a `..` after a directory that
    exists climbs from that directory's real path, as the kernel does, round 3, 2026-09-19; a link the same command
    creates is resolved only when it is an `ln -s` with literal operands the hook can place and an untouched name,
    class H; every other same-command link or mutation makes a later write through the name refuse, family 3 and
    rule (c) of the third pass, below). The refusal is exit 2 with one
    line naming the file and the track-edit command, in the person's voice. What it lets through: a read (cat,
    grep, diff, git, sed without -i) names no target; a command behind eval, xargs or a shell -c it cannot read
    is unresolvable and passes, since a silent block of ordinary work would cost more than a missed write (so does a
    script piped into a shell from a producer other than a literal echo or printf, and one handed to a shell outside the
    set the guard reads, busybox sh or ash among them: the second fix-up of round 5's fifth addendum names both; since the
    third fix-up, a script a `${...}` word stands for when the guard cannot read the word, one fed by a redirection on the closing
    brace of zsh's brace-body compound, and one a command named by an expansion runs, named among the writers below), and
    so does a python or node one-liner whose write path is computed (a name, an f-string, `sys.argv`,
    `os.environ`), since the interpreter scan reads a literal path only (the round-1 review of 2026-09-18
    rejected a scan of computed paths by execution: it would refuse ordinary scripting and still miss the
    common forms); a write whose target the hook cannot read (a variable, a `$(...)` or a backtick, a `~user`, a
    brace list past the cap, or a glob that matches nothing or names more than the hook will list) is refused
    while a project that tracks anything is in play, that is when the session's cwd, the directory a `cd`
    moved to, or the folder a copy lands in sits under a config whose tracked list holds an entry the literal
    rule could refuse (a text name the veto list does not cover, or a note the link closure reaches from one),
    the directory judged under its real path and its name, and the landing folder counting only when a tracked
    file could land there (a refusable entry at or below it, an existing entry there that is guarded or links to
    a tracked file, or a note the closure reaches below it) or when it holds more than 2000 entries, past which
    the hook does not scan it and takes it as in play (`LANDING_SCAN_CAP`, a deliberate false refusal, pinned on
    both sides of the boundary and escalated with the change; review round 2, 2026-09-18), and passes with no
    such project in play (2026-09-18, after a research session's report through the box admin, 2026-09-17: a
    `cp` built from shell variables landed raw on a tracked file beside a refused literal one; the round-1
    review the same day bounded the rule so that a temp log or a copy into an untracked folder is not refused
    across the box once one project tracks a file); a landing folder no project claims counts when an entry of it is
    or leads to a tracked file whose name the copy could take (round 3, 2026-09-19: `cp "$SRC" <outside>/` over a link
    there onto a tracked file overwrote it while the same copy spelled out was refused; past 2000 entries such a folder
    is not scanned and the copy passes, a stated residual, since a folder no project claims carries no case for a
    blanket refusal); the project the target's own literal directory part sits in is asked first, from any cwd, for
    every target the hook cannot read that it can place, absolute or relative to a write-time directory it knows, when
    a tracked file could land in that folder (round 2 for a numeric target; round 3 for every unreadable word and for a
    relative spelling, after `cp x <project>/notes/$N.md` from a cwd in no project overwrote a tracked note while
    `<project>/notes/`, the literal name and the numeric spelling were all refused); a literal relative target after a
    `cd` the hook cannot follow (one to a name the shell fills in, `cd -`, `popd`, one inside an if, loop or case body,
    or one to a directory the command cannot enter when the hook runs, which it may make first or which the cd fails
    on, leaving the shell where it was) is refused while the cwd's project is in play, with the reason and the remedy
    (an absolute target, or a `cd` to a literal directory that exists), where before it was dropped (round 3: one such
    `cd` turned a refused write on a tracked file into an allowed one; the cost, a `mkdir -p build && cd build && cmd >
    log.txt` from a tracked cwd, is a deliberate false refusal); one narrowing from the round-1 review, corrected by its
    round 2 and again by round 3 (2026-09-19): a target whose only expansions are `$$` and `${$}`, the shell's process
    id, and whose text is an absolute path outside every project in play is allowed, since such an expansion cannot
    carry a `../` back in. The numeric set is those two spellings and nothing else, in every shell: every other
    candidate can be unset or shadowed by the command and then hold a path (round 1 listed `$RANDOM`, `$SECONDS` and
    `$BASHPID` as read-only integers; round 2 dropped BASHPID, which zsh leaves assignable, and kept the other two
    under bash and zsh; round 3 measured `unset RANDOM; RANDOM=../x` and `local RANDOM=` in a function in bash,
    `typeset -h RANDOM` in a function in zsh and a sourced file carrying the unset, each carrying a traversal onto a
    tracked file while the hook read the word as numeric; `$$` resists every road in bash, zsh and dash), so a
    `log.$RANDOM` inside a tracked project is refused, a deliberate false refusal recoverable in one step (`$$`, the
    literal spelling, or a write outside the project), where an overwrite with no change recorded is not. A numeric
    target is judged by where it lands: the project its own literal directory part sits in first (a numeric name
    landing in a second tracked project is refused from any cwd, the refusal naming that project), that part resolved
    through the filesystem (a link in it, a `..` after one), each entry of that directory that exists now and whose
    name the process id could spell (`x-4242` for `x-$$`) followed as the write would follow it, and a fold that
    leaves no expansion handed to the literal rule (round 3: a pre-existing link named by the number, a fold onto a
    link to a tracked file, and a literal `..` after a link were each folded away before the resolve step and a write
    landed on a tracked file); the landing gate on that literal directory part is folder-granular, so a numeric name
    in any folder where a tracked file could land is refused from any cwd while its literal spelling may pass,
    `<root>/x-$$/y.md` and `<root>/docs/build-$$.log` alike, a deliberate false refusal ruled correct in round 2's
    addendum (2026-09-18) for the first segment (the folder's name does not exist at check time and is not derivable
    from the text, so the hook cannot tell which folder of the project the write lands in, a person recovers in one
    step, and the opposite error overwrites tracked content silently) and restated by round 3 as the gate rather than
    the segment, since `<root>/docs/x-$$/y.md` is refused the same way when docs/ holds a tracked file; the refusal
    names the unknown folder when the expansion names one, at any depth, and offers a literal folder name or a write
    outside the project, never the name the shell would give it, which nobody can know before the command runs; a
    folder of more than 2000 entries inside a tracked project refuses a numeric name unscanned, as it does a copy
    (`LANDING_SCAN_CAP`, both sides pinned); a segment that is nothing but an expansion cancelled by a `..`
    (`<out>/$$/../x.md`) is not narrowed. Two things the rule does not see, stated: a link the same command creates
    under or after the numeric segment (the pid-candidate scan reads only entries that exist when the hook runs; the
    class-H rewrite that follows a same-command `ln -s` with literal operands runs for a literal target, not for the
    candidate scan), and an entry
    named by the process id in a folder outside every project that holds more than 2000 entries, which is not listed
    (a fail-closed cap there would refuse every temp log in a large `/tmp` from a tracked cwd; the box's `/tmp` held
    2767 entries when measured). A relative numeric target stays refused even when the write-time directory is known
    and outside every project in play, since the allowance needs an absolute path; a variable of unknown content, a
    substitution (a `$(date)` in a log's name among them, a cost stated to the user rather than solved) and a bare
    expansion stay refused; `$'...'` is ANSI-C quoting in bash and zsh, a literal word (round 3: it was a non-literal
    word dropped from a cwd in no project, and bash wrote the tracked file), one the hook cannot read inside a script
    handed to `sh`, `dash` or `ksh` (dash reads a literal dollar), and `$"..."` stays one the hook cannot read; a
    bare, escaped or quoted `$` is a literal dollar, so a folder or a project whose name holds one is judged by that
    name (round 3: every dollar in a word read as an expansion, with a false refusal one way and an allowed write
    into a tracked folder the other); `bash -O extglob -c '...'` and an option cluster holding `o` or `O` take their
    word, so the script is read (round 3; it was taken as the operand); a command nested past 64 substitutions or
    brace lists is marked opaque rather than followed, so it cannot overflow the stack, which evaluate read as allow
    (round 3); the hook reads no variable of the ENVIRONMENT named in the command to
    resolve the word, which would read names shaped like secrets and guess at the cwd (of the environment it
    reads HOME, for `~` and a leading `$HOME` as the shell does, TRACKCHANGES_ROOT, which stands in for the root
    search only for a directory under it, and ROMP_SID; of those only HOME's value can appear in a refusal, and
    only as a path the hook resolved through it, the target a `~/` or a leading `$HOME` names or the project
    root a bare `cd` lands in, while TRACKCHANGES_ROOT is named by the variable, never by its value, and
    ROMP_SID is never printed; since B2, below, it does read a name the command's OWN TEXT sets to a plain string,
    and PWD and OLDPWD from its own directory model, and a refusal can show such a value, so the sentence as it
    stood before round 5 of the review, that no variable the command names is read and only HOME's value can
    appear, was false from B2 on); a glob is otherwise
    expanded against the filesystem as the shell expands it (a redirection onto several matches or brace
    alternatives names each, as zsh's multios writes them; bash writes none), a brace list is expanded before
    the operands are read, a here-string is scanned like a heredoc and a process substitution's command is read
    like a `$(...)`; a tracked image or PDF passes by name as in the vendored guard; a source copied out of a tracked
    file is a read. Not read: rm, a mv of the tracked file elsewhere (a rename the store heals by content hash),
    find -exec, rsync and patch. Round 4 (2026-09-19, a walk-around lens) closed eight more in-model roads: cp,
    mv, install and ln read a per-writer option table (`COPY_OPT`), so a no-argument flag (`-Z`, a bare
    `--context`) no longer eats an operand and an option the table does not know refuses the command; `env -C DIR`,
    `env --chdir=DIR` and `sudo -D DIR` run the inner command in DIR (`commandOf` returns its `chdir`); the
    `PREFIXES` set gained `setsid`, `flock`, `taskset`, `chrt` and `numactl`, each peeling its operand (`flock … -c`
    read like `sh -c`); a same-command assignment to HOME makes `$HOME` and `~` unreadable (the lexer marks a home
    expansion 'h' and `extract` computes `homeAssigned`); a word whose literal head parents a tracked root
    (`parentTrackedRoots`) or sits under one (`ownProjectFor` returns the root without the landing gate) is refused
    unless every expansion is numeric; a directory the hook cannot search before a `..` is refused, not folded
    (`foldSegments` folds a `..` through the real path and lets a stat error there propagate); and a symlink an `ln
    -s` makes earlier in the command redirects a later literal target (`recordSymlink`, `applyInCommandLinks`). The
    walk-around lens second pass (2026-09-19) then closed six families of in-model write the hook read yet let through,
    each stated as one rule. (1) OPTION TABLES: the per-writer tables and `sort`'s `-o` accept a glued short form
    (`sort -oFILE`), and `env -S`/`--split-string` runs a shell string, read like `flock -c`, not skipped as an operand
    (`commandOf`). (2) ANY ASSIGNMENT FORM: HOME, the one variable the guard expands, as an lvalue in any form the
    shells offer (`HOME=`, `HOME+=`, `export`/`declare`/`typeset`/`local`/`readonly HOME`, `read HOME`, `printf -v
    HOME`, `mapfile`/`readarray HOME`, `env HOME=… cmd`, `getopts … HOME`, `for HOME in`) makes `$HOME` and `~`
    unreadable for the whole command (`assignsHome`). (3) IN-COMMAND PREFIX MUTATIONS: an earlier `rm`/`rmdir`/`mv`/hard
    `ln`/`cp -l`/`cp -s` that removes, renames or aliases a path makes every later word under that prefix unreadable
    (`mutated`, `recordMutations`); the `ln -s` class-H rewrite is kept only when nothing else in the command touched
    the link name or its source, and a relative link source resolves against the LINK's directory. (4) STAT ERRORS
    REFUSE: a stat, lstat, realpath, readdir or config-read error other than ENOENT anywhere on a judged path (a
    mode-000 parent, a mode-000 tracked folder or `.trackchanges`, the whole project mode 000) is an answer the hook
    does not have, so it refuses from any cwd, naming the error and the path (`UnknownPath`, the class-G flip applied to
    every judged path, since a directory it cannot search may itself be a tracked project; the cost, a false refusal of
    a write under a directory the session may not search, is recoverable in one step). (5) NESTED MARKERS: a `.git`,
    `.obsidian` or `.trackchanges` between a tracked project's root and the target refuses, naming both markers
    (`outerTrackingRoot`); store-io's nearest-marker rule stays for the untracked case. (6) A cd THE GUARD CANNOT KNOW
    leaves the directory unknown from that point (as `cd -` already did), so a later literal relative target refuses
    with the construct named: a cd after `&&`/`||`, a cd in a pipeline or backgrounded, a cd under a wrapper, `pushd
    -n` or a rotate, a physical cd (`cd -P`, after `set -P`, or an option not modelled), and a call of a function whose
    body ran a cd; `env -C DIR` resolves its operand physically, as chdir(2) does. The guard states its contract on the
    hook header, the vendored skill, hooks/README.md and docs/install.md: it is best-effort against known write forms,
    its default on an unrecognised form is allow (deliberately not flipped, since flipping it would refuse almost all
    normal work), the one class flipped to refuse is a path it cannot check (family 4), and the unmodelled writers that
    still reach a tracked file are listed.
    The walk-around lens third pass (2026-09-19) re-keyed six rules on what the guard can see, after a third attack
    walked around each enumeration with the next spelling (a nameref and `select HOME in`; a glued `env -Cdocs`, an
    abbreviated `env --chd=`, a nested `env -C docs env -C ..`, an `env -S` string beginning with env's own option; a
    non-literal `ln -s` source; zsh's `set -o chaselinks`; a two-segment expansion under a grandparent; `cp --targ`
    from a cwd in no project). The reviewer's rule, paraphrased: a rule implemented as an enumeration of spellings is
    a case list, and the next spelling walks around it; a rule is keyed on a token, an unparsed option, a non-literal
    operand or the presence of a construct. (a) BARE IDENTIFIER: the identifier of a variable the guard expands (HOME,
    `EXPANDED_NAMES`) anywhere in the command outside a `$`-expansion makes that expansion unreadable for the whole
    command and a bare `cd` or `cd ~` unknown (`bareExpandedNames`). (b) FULLY PARSED OR REFUSED: every wrapper in
    `PREFIXES` is parsed against its own option table (`WRAPPER_OPT`) or the command refuses naming the option (an
    unknown, abbreviated, glued-unknown or non-literal one), the words after it judged by their own project; a nested
    chdir composes (`commandOf` returns its `chdirs` in order); `env -S`/`--split-string` and sudo's -e, -i, -s, -R and
    -h are opaque and refused outright, never recursed; `time -o FILE` is a write of FILE. (c) NON-LITERAL LINK SOURCE:
    a symbolic link whose source the guard cannot read or place marks the link name as mutated, so a later write
    through it refuses (`recordSymlink`). (d) SHELL OPTIONS, AN ALLOWLIST (the reviewer's recast, 2026-09-19): an option
    on `set`, `shopt`, `setopt` or `unsetopt` not on the inert lists (`INERT_SET_LETTERS`, `INERT_SET_OPTIONS`,
    `INERT_SHOPT`, built from the shells' own option lists: exit status, tracing, history, completion, prompts, job
    control and syntax choices that move no path) leaves the directory unknown from that point (`shellOptionChange`);
    every option about cd, pushd, physical paths, links, globbing, brace expansion, aliases, quoting, restricted or
    POSIX mode is off the lists, so its gap is a false refusal. (e) ANY DEPTH: the parent-prefix rule finds every
    tracked root under the literal head at any depth, breadth-first within `PARENT_SCAN_BUDGET` entries
    (`parentTrackedRoots`). (f) UNKNOWN OPTION REFUSES EVERYWHERE: an option a writer's table does not know refuses on
    every path the writer is reached through, each candidate operand judged by its own project from any cwd
    (`optionCandidates`), and the mutation and symlink recorders mark every candidate. Also from that pass: `chdir`
    (zsh's and dash's cd, no command in bash) leaves the directory unknown, and coreutils `link` is a hard-link maker.
    The hook header audits every list that remains for the side its gap falls on. The cost is measured against
    `tools/romp-track-bash-guard-corpus.json` (164 ordinary developer commands and the 22 recorded false refusals, run
    at the head before the pass and at this one): no ordinary command newly refuses; the refusals added are a `~/`
    write beside a mention of HOME, an `env -S` line, a relative write after `shopt -s globstar`, a write through a
    link whose source is a variable, and a variable-named file in a folder with a tracked project anywhere beneath it,
    each pinned with its remedy. The contract paragraph is identical on the four surfaces, its allow-by-default
    sentence and its refused-class sentence included, and its writer list names the out-of-model roads the passes
    found (a sourced or eval'd script, a wrapper outside the set, shuf -o, a cd through CDPATH).
    The fifth commit (2026-09-19) closed the fourth pass's misses as rules on visible constructs, on the reviewer's
    ruling, and settled two boundary questions. M6, first: 576 of the dollar matrix's refusals put a shell-live `$`
    inside the double quotes of the remedy's `--file "..."`, so the pasted line named another file in bash and a third
    in zsh; `trackEditLine` single-quotes the argument (`shellQuote`, a quote inside the path as `'\''`), pinned by
    running the pasted line through real bash and real zsh against a stub that prints its argv. M1: a name operand that
    carries an expansion, a substitution or is itself a quoted expansion on an assignment, declaration, nameref, export,
    typeset, local, readonly, read, mapfile, getopts, unset or `printf -v`, or an expansion in lvalue position of a
    `let` or `(( ))`, marks every expanded name unreadable for the whole command and a bare `cd` unknown
    (`assembledNameOperand`, `homeUnreadableWhy`), since `export ${h}${m}=<dir>` reassigned HOME with no literal token;
    a literal name other than HOME and a read-only twin change nothing. M2: the lexer consumes zsh's clobber-override
    `!` and `|` after `>`, `>>`, `>&`, `>>&`, `&>` and `&>>` (`clobberSuffix`), records the operator as spelled, and
    records bash's reading beside zsh's (a file named `!`, or `!word` when glued), so a command refuses when either
    shell would write the tracked file. M3: `extract` returns the command's class-H links and `evaluate` follows them
    while it places the targets it could not read, so a numeric target's literal directory part is folded through a link
    the same command makes before it; a numeric or opaque word under a prefix an earlier command mutated is refused with
    the family-3 reason (`mutatedUnderLiteralPart`). M4: a `$` inside a plain interpreter string is text, so a literal
    path is kept and judged by name (the `[{}$]` filter and the node classes' `$` exclusion are gone), and a template or
    format string (an f-string, `.format(`, `%`, a template literal with `${`) is returned as unreadable
    (`scriptTemplateTargets`, the `templatePath` refusal) while a computed path stays out of model. M5, THE CRITERION:
    an option earns a place on an inert list only if it changes neither how a word is expanded, matched or split, nor
    where a relative path resolves, nor which grammar is in force; every entry carries its one-line reason
    (`INERT_OPTIONS`, exported for the data-driven test), verified against the option descriptions of bash 5.2.21, zsh
    5.9 and dash 0.5.12 on this box and by execution where a description left a doubt; the eleven the fourth pass found
    came off with twenty-six more `set -o` names, twelve shopt names and six letters, and bash's `set -k`, measured
    writing a tracked file through a `cp` the guard read as writing nothing, is read both ways (`setsKeywordMode`). B1
    (ruled yes): a record that aliases a source (a hard `ln`, `cp -l`, `cp -s`, `link`, a symbolic link whose source the
    guard cannot read) carries the source, and the in-play question for a write through it is asked of where the write
    LANDS, the source, from any cwd (`aliasSourceInPlay`): a source in a tracked project puts that project in play, a
    source the guard cannot read refuses from any cwd, a source outside every project is allowed. The cost, measured
    against the corpus (196 entries, run at the head before the commit and at this one over one world): none of the 164
    ordinary commands newly refuses; the five entries added are a `~/` write beside a `printf -v "$name"`, a relative
    write after `set -f` and after `shopt -s nocasematch`, an f-string path from a tracked cwd, and a write through a
    link whose source is a substitution from a cwd in no project. The contract paragraph on the four surfaces names the
    variable name the shell fills in, the template path and the alias among what is refused, and the interpreter's
    computed forms, the unbounded class of command-running wrappers and a link made by an unmodelled writer among what
    still reaches a tracked file.
    B2 (the second commit of the fifth pass, 2026-09-19; the reviewer's ruling with its condition, then the reviewer's
    option (c) on the measured delta: the resolution half kept, the refusal half dropped; the dropped sequence is fork
    PR #780's cb0b15422 and 24acdce20): a literal head outside every project bounds nothing once an opaque expansion
    follows it (the matrix's `x='../sub-on/p$abc'; printf poison > <out>/$x/rep.md` from a cwd in no project). `extract`
    now RESOLVES every expansion whose value it can read before judging a word (`resolveWord`, `valueOf`): a name the
    command set to a plain string earlier, at the top level in plain sequence (`recordPlainWord` and `recordSegment`
    since the seventh pass, the readability rule's predicate, which mark a name
    set in a body, a subshell, after `&&`/`||` or in a `{ }` group opened after one of them, by a `read`, a loop, a nameref, an unset or a `+=`, or any name once
    an eval, a source, an unknown wrapper option or a call of a function the command defines ran, as unreadable); HOME
    through the guard's home; PWD through the directory it knows; OLDPWD, `~+` and `~-` through the directory before a
    `cd` in the same command; none of HOME, PWD and OLDPWD once the command names the name outside an expansion or may
    fill it in (`EXPANDED_NAMES` names every name `valueOf` substitutes and `unreadableExpandedNames` returns each the
    command may reassign with its reason, rule (a) and M1; B2's first draft read `$PWD` and `$OLDPWD` through the
    guard's own directory model while the command reassigned them, so `PWD=<web>; cp <web>/base/report.md
    $PWD/docs/report.md` from a tracked cwd wrote the tracked file, the fifth pass's attacker found; the refusal says
    why the name was not read); a `$(...)` in a subshell inherits a copy of the names, a script handed to a named shell
    none. The resolved word is judged as literal (`x=other.md; echo hi > docs/$x` by name; `x='../docs/report.md'; cp
    base/report.md scratch/$x` refused by name; attack 1's `~-` road and attack 2's `scratch/$v` road closed the same
    way). What stays opaque keeps the verdict the working directory gives it: refused as not literal from a cwd in a
    tracked project (class F and the cwd rule, as before B2), dropped from a cwd in no project. THE PRINCIPLE (the
    reviewer's): a guard is strictest where its subject is and loosest where its subject is not; this guard's subject is
    tracked files inside projects; from a tracked cwd an opaque expansion is refused before and after B2, since that is
    where the danger and the user's intent live; from a cwd in no project the guard reaches furthest from its subject
    and must not refuse on a value it cannot know. The threat model is the user's own box against accident, not malice:
    for the dropped refusal half to be worth the refusals it added, an accidental opaque value would have to hold a
    climbing relative path AND land on a tracked file, issued from a cwd outside every project; a variable holding
    climbing relative text is rare by accident, a user in a scratch directory writing `$USER.log` or `$(date +%s).md` is
    ordinary, and a guard that refuses ordinary work gets switched off. THE RESIDUAL, with its boundary, on the four
    surfaces: a literal head outside every project followed by an opaque expansion whose value can climb with `..` is
    allowed from a cwd in no project; from a tracked cwd the refusal stands unchanged. The cost, measured
    (tools/romp-track-bash-guard-corpus.json, the b2-readable and b2-opaque entries, 44 shapes run from a cwd in no
    project and from a tracked one; a sample of shapes, not the population of commands, so the principle decides and the
    count describes): none of the 164 ordinary commands changes verdict; the 22 readable shapes refuse 3 times after
    resolution, each by name on a tracked file the value reaches (one of them a live overwrite before), and 20 of their
    22 refusals from the tracked cwd became allowances; the 22 opaque shapes keep their verdicts, refused from the
    tracked cwd and allowed from the cwd in no project; three recorded false refusals from earlier passes are allowed
    now that their value resolves (a `$PWD` link source, an `x=scratch` class-E entry, a `~+` spelling), and one cost
    entry is added, a `$PWD` write beside a mention of PWD from the tracked cwd.
    The pin addendum (2026-09-19; the fifth pass's mutation lens found seven B2 claims no test held, and its attacker
    seven in-model overwrites; the second commit of the ruled sequence) pinned five of the claims from the tracked cwd,
    where an unresolved name is refused and a resolved one judged by name (a mid-word `$HOME` beside a mention of HOME;
    a loop variable, a `read`, a `mapfile` and a `getopts` into a name set earlier; the copy of the names a `$(...)`
    inherits; the fresh scope of a `flock -c` string; and beside them resolution under a bare `.git` repo, each with the
    real-shell landing or the clean twin run, and each opaque row pinned allowed from a cwd in no project, the residual
    with its boundary); the poison of an unknown wrapper option and of an `env -S` string (the other two)
    is not pinned, disclosed for a ruling (an external command cannot reassign the calling shell's names, so whether
    that poison stays is the reviewer's call, and a pin would fix one side of it). The addendum closed the overwrites,
    each a stated rule applied to a construct the guard could already see, no rule added (the PWD and OLDPWD finding is
    closed in B2's
    own commit, above): `cp --parents` lands each source at its whole spelling under the destination (`under` in
    `copyTargets`; the flag was known and its landing computed as the basename); python's short options are read as a
    cluster the way python reads them, `-c` and `-m` taking the rest of the word or the next word and `-W` and `-X` a
    value (`-c'CODE'`, `-uc'CODE'`, `-Xutf8 -c'CODE'`, `-bc'CODE'` and `-Ic'CODE'` were skipped as unknown options);
    node's `--eval=CODE` is its code and `--print=X` a flag (node then reads the script from stdin, measured); a
    triple-quoted python string is the plain string it is (`pyStringArg`'s delimiter is three quotes or one) and a JS
    string body runs to the next quote of its own kind, so a template literal holding a quote is a template (`nodeStr`).
    The cost, measured against the corpus (285 entries): none of the 164 ordinary commands newly refuses. The contract's
    writer list names a concatenation and an escape sequence among the interpreter paths that pass
    (`open("docs\x2freport.md","w")` lands, measured), and the four surfaces carry the addendum's sentence.
    The sixth pass (2026-09-19; the mutation lens over the ruled sequence's head ran seventy-five mutations and found
    thirteen green, each a claim the code made that no test held) pinned nine of them in both directions, the refused
    row run unguarded in a real shell and every allowed row run with the tracked subset fingerprinted after: the
    unreadable-name marks reach a `$(...)` (`unreadableNames` in the recurse context; PWD reassigned outside and `$PWD`
    inside, bash and zsh wrote another project's tracked file); a cd the guard cannot follow leaves OLDPWD unknown
    (`moveUnknown`; `cd docs; cd "$(pwd)"; cp <src> $OLDPWD/report.md` overwrote the tracked file through the stale
    value); a nameref, a `printf -v` and a `readarray` into a name set earlier make it unreadable (`recordAssignments`;
    bash landed the write in the tracked folder through each); a `$(...)`'s own assignments do not come back (the copy
    of the names; a shared map refused the write by name, falsely); an empty value is not read (`resolveWord`); with
    `cp --parents` a destination that is not there is read as a directory (`copyTargets`; cp writes nothing without it,
    and the guard's reading of the landing is what refuses); python's `-m` ends the option walk (a heredoc after
    `-mjson.tool` is the module's stdin data, allowed and run). The `recordAssignments` line that poisoned the names
    after an unknown wrapper option, an `env -S` string or a `flock -c` string was unreachable (each branch continues
    before `recordAssignments` runs; the first two poison in their own branches of `extract`) and is removed, and a
    `flock -c` string is pinned as it measures, no poisoner. Not pinned, for a ruling: whether the poison of an unknown
    wrapper option, an `env -S` string and `xargs` stays (an external command cannot reassign the calling shell's
    names; both sides are observable once ruled: from a tracked cwd the refusal's class, from a cwd in no project the
    verdict). No verdict changes: the corpus's 285 entries keep theirs.
    The seventh pass (2026-09-19; the sixth pass's attacker on 86c0643ec, whose report the workflow that ran it read as no
    finding when the agent died on 529s, so the pin addendum's commit message and the PR body said the attacker filed none)
    found 77 in-model live overwrites in 13 spelling classes, each a value the command spells that the resolution half
    resolved to a string the shell does not produce, judged the wrong path and allowed while the shell wrote a tracked file
    (0 structural). They are closed as one rule, THE READABILITY RULE, stated once at the resolution half (the comment at
    `RESOLVED_NAME`) and on the four surfaces' contract paragraph, and implemented as one predicate (`plainSequence`,
    `plainValue`, `recordPlainWord`, `recordSegment`, `taintWord`): a name is readable only when every write to it in the
    command is a plain top-level `NAME=plain-string` the shell performs as spelled, and any other construct that can write it
    makes it unreadable from that construct on (a plain write after it does not restore it), keyed on the construct's shape
    (an lvalue-shaped word in any position, the bare identifier as a whole word or a token of a word that is not an option,
    an assignment inside a `${x=..}` or `${x:=..}` expansion, a name in an arithmetic body, `identifierTokens`) and never on a
    list of commands, the reviewer's framing being B2's own unknown-defaults-to-unreadable doctrine, already applied to a
    `read` and a loop variable, applied to assignment. The classes: a tilde opening an assignment value (`plainValue`: `~/`
    and `~` resolve through HOME, `~+` and `~-` through PWD and OLDPWD, a `~user` and a tilde after a `:` leave the name
    unreadable); a declaration flag that transforms the value (at that pass `INERT_DECLARATION_FLAGS`: `-g`, `-x`, `-r` and
    `--` alone were inert; since round 5's addendum no option word is, and `ATTRIBUTE_ONLY_FLAGS` picks the refusal's text
    alone); a nameref (the target tainted, `refTargets`, or every name when the target is one the shell fills in); an
    assembled name operand (the resolved name tainted when it resolves, every name when it does not); scoping (a pipeline's
    tail, a `{ }` group whose closing brace is piped or backgrounded, which also restores the directory, a wrapper's
    argument, `commandOf` returning the assignment words as a nameless command's arguments, an assignment-only segment's
    words read left to right); functions (`function NAME {` is a definition, and a call by the head as spelled, a wrapper's
    name included, poisons every name); a subscript. Found with the fix, the same rule's unlisted spellings: an eval that
    assembles `HOME=` then a `~` write (the poison covers HOME, PWD and OLDPWD, `homeUnreadableNow`), zsh's `print -v x`
    and `${x::=..}`, and a piped `{ cd docs; }` group whose cd was followed. A plain `unset NAME` in plain sequence resets
    the name (the shells drop its value and attributes, measured), so a plain write after it is readable again. From a
    tracked cwd every one of the attacker's 62 rows there refuses, by name where the value resolves and as not literal with
    the construct named otherwise; from a cwd in no project the 15 rows the guard resolved wrongly split into 5 refused by
    name and 10 the ruled residual (an opaque expansion after a literal head outside every project, allowed and landing,
    the boundary B2 states). The cost, measured against the corpus (285 entries, no verdict changes) and the dollar matrix
    and stated in the PR body: a `~/` value resolves through HOME at no cost; `declare -i x=5` (and `-a`, `-A`) then `$x`,
    `let x=5` then `$x`, a pipeline-tail assignment (which zsh keeps) and a piped plain group then `$x` each refuse from a
    tracked cwd where the shell's value was known. The addendum the same day, four items: a plain top-level `HOME=<path>`
    assignment is the one readable write to HOME (`readableHomeWrites`), read for the commands after it (a bare `cd` is
    resolved against the cwd like `cd <dir>`; a bare `pushd`, which bash and dash fail and zsh takes home, leaves the
    directory unknown, a live overwrite since before this pass), inherited by a
    `$(...)` and by a script handed to a named shell (the shells keep HOME exported), with the prefix form `HOME=<path> cmd`
    excluded and refused with its own reason (`unreadableExpandedNames`, kind `homePrefix`), since bash, zsh and dash expand
    cmd's `$HOME` and `~` before the prefix applies and cmd runs under the new HOME; the refusal for a cd under `builtin`,
    `command` or `time` says what each shell does (`WRAPPED_CD_WHY`: bash and zsh move under `builtin`, bash and dash under
    `command`, bash and zsh under `time`; the verdict stays unknown) where it said the shell does not move; the prefix
    form's own text; and the test file's real-shell evidence legs run through one probe that reports a shell that is
    missing or too old with a `NOT RUN` line per leg, never a silent pass (zsh since the addendum; dash, the bash legs and
    a bash below the 4.3 the legs need since round 5 of the review, whose `spawnSync` wrapper throws by name when a leg
    reaches a shell the probe declined).
    The seventh pass's attacker (2026-09-19; on 93bb93b68, at the rule's own boundary) found two misses, 0 structural, each
    a construct the lexer already produced that the implementation realised at one level only, and the close found a
    sibling beside its readonly rows. F2, a `{ }` group nested in a piped or backgrounded group (13 live rows in bash, zsh
    and dash, a cd face included): one frame opened for the first `{` and popped on the first `}`, so the piped outer brace
    was never a subshell boundary; the group frames are nesting-aware (`openGroup`, `closeGroups`: a group closing in plain
    sequence hands its names to the enclosing group, a piped or backgrounded close taints every name and restores the
    directory, and a trailing `}` closes after its segment, `pendingClose`), and a declaration inside a group notes its
    name (`noteGroupName`: `{ declare x=..; } | cat` kept x readable at one level). F1, zsh's precommand modifiers
    `noglob`, `nocorrect` and `-` (`ZSH_MODIFIERS`; 14 live rows in zsh alone, bash and dash failing on the word and
    writing nothing) were read as commands named so and hid the writer behind them; they are wrappers of the shape of
    `command` and `builtin`, with an empty option table and a `WRAPPED_CD_WHY` text for a cd behind one, and the wrapper
    list on hooks/README.md, docs/install.md and the vendored SKILL.md names them. RO: a name made readonly then written by
    a `declare`, `typeset`, `export` or `unset`, which bash refuses and continues past with the readonly value (dash too
    where the word is no command of its) while the guard adopted the later one (`readonly x=docs/report.md; declare
    x=scratch/keep.md; cp base/report.md $x` wrote the tracked file in both); a readonly name keeps its value and every
    later write is skipped (`readonlyNames`), the one write outside the plain form that resolves at no cost, and a `+r`,
    which zsh honours, is a flag outside the inert set and taints as before. The one twin that moves: `command noglob cp`,
    allowed before and refused by name now, a spelling no shell runs. The mutation lens's unpinned claims are pinned row
    by row in the test file, and its shadowed poison (a declaration's option word the shell fills in, which M1's
    per-segment detector reads first on the same word) is removed.
    Without ROMP_SID it exits 0 before reading stdin (decision 24). Cost: about 60 ms
    per Bash call when no target needs the link closure (a read, a literal target outside any project, an explicit
    hit on the project's tracked list, an empty list); a write to a file inside a tracking project that the list
    does not name (the common write in a project that tracks anything) adds one walk of the project's markdown
    tree per call, store-io's `trackedClosure`, a listing of every .md under the root and a read of every tracked
    note, the same walk the vendored guard pays on every such Write, built once and shared by all the command's
    targets, so a directory copy pays it once: measured at 80 to 100 ms on a 3000-note tree and 130 to 170 ms on
    a 12000-note one, more under load, growing with the project's markdown count and well under the installer's
    10 s timeout. A write whose target the hook cannot read pays the same walk only when the tracked list alone
    does not settle whether its project is in play (a figures-only or fully vetoed list, or a copy whose literal
    landing folder has no refusable entry at or below it, which also pays a listing of that folder and a guard
    check of each of its entries first, up to the 2000-entry cap), a numeric target outside every project
    included when the cwd's project lists nothing refusable; then one walk per call, shared with the literal
    targets; none when a listed refusable entry settles it, and none when the list is empty (review round 2,
    2026-09-18; `tools/file-review-plan-bash-guard-review.test.mjs` counts the walks).
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
    Round 5 of the review (2026-09-20; the reviewer's round-4 ruling over the seventh pass's head: twenty-nine findings,
    seven highs, six of them one defect, and none refuted) closed two root causes and their riders. THE FRAME ON PARSED
    STRUCTURE: the frame decision (a body that may not run: its names unreadable, its `cd` unknown at the closer) was keyed
    on the segment's FIRST word, so a leading `!`, `time`, `{`, a `then` or `do` before a nested head, and `select`, which
    COMPOUND_HEADS listed and neither the push nor CLOSERS did, hid the head, no frame opened, and the body was walked as
    this shell's own plain sequence (the name adopted, the `cd` followed, so the wrapped spelling walked around round 3's
    unknown-directory refusal by being confidently wrong instead of unknown). The head is read after a peel of everything
    the shell reads past before a reserved word (`peelIndex`, `compoundHeadOf`, `FRAME_PEEL`, `TIME_OPTIONS`: `!`, `time`
    and its `-p` and `--`, the braces, `then`, `do`, `else`, `elif`, the wrapper words and assignment-prefix words), at the
    brace scan, at both head reads and at the function-name reads (`! f() {` and `{ f() {}; } | cat` are definitions),
    re-peeling between braces; the push, CLOSERS and COMPOUND_HEADS read ONE table (`BODY_CLOSER`), so `select` fell out of
    it; and a function body's closing brace is counted once (`braces` returns the enclosing scope's index; it was counted by
    the group scan too, closing a piped group one brace early). PEEL FOR THE FRAME, NOT FOR THE FREEZE: `frozen` was read
    from the peeled command, so `env readonly x=..` froze a name no shell froze and the guard kept a stale value while the
    later plain write went through, the one place the rule's failure was an allow; the freeze now needs the segment's own
    unwrapped `readonly`, `declare -r` or `typeset -r` (`!cmd.wrapped`), and a declaration behind any wrapper taints its
    names (the shells differ on whether it ran: `command readonly` freezes in bash and dash, `builtin readonly` in bash and
    zsh, `noglob readonly` in zsh, the external wrappers nowhere, measured; round 5's addendum, 2026-09-20, narrowed this
    further, below: the freeze is an unwrapped `readonly` with no option word in plain sequence alone, and `declare -r` and
    `typeset -r` taint, dash having neither). THE CATCH-ALL REFUSES: `Object.hasOwn` at the
    CLOSERS and BODY_CLOSER lookups (a command word that is an Object.prototype key threw inside a body), and any exception
    evaluate did not anticipate refuses while a tracked project is in play, naming it (`judge`, `internalErrorRefusal`; two of the three catches that allowed rethrow to the one catch-all, and the
    process-level catch refuses in place). THE CENSUS DERIVED: the hand-written census of the lists that remain, which omitted
    the two write-side lists this round's highs lived in, is replaced by one computed from the hook's source at test time
    (`tools/romp-track-bash-guard-census.mjs`: every column-0 `const`, `let` or `var` whose initializer opens a Set, an
    array, an object table, an `Object.fromEntries(` or a `new RegExp(`, the writer cases and the root markers, each
    classified against its consumer line; a list the census does not name reds the test;
    it corrected one stated side, an interpreter option not on `INTERPRETER_OPERANDS` being a write gap, measured, not an
    over-count, disclosed and unfixed). THE DRAW WIDENED: the rule pin's UNLISTED set spans the scope half of the rule (a
    body behind `{`, `!`, `time`, a select body, a function body in a group, a subshell, each closer). The riders: a node
    or python path that opens with a string literal and goes on is a template (`nodeStringArg`, `pyStringArg`; the base
    refused it and round 4's head let it through); a `>&` dup is exactly a digit run or `-` before a delimiter and `>>&`
    is never one (`printf x >&2-3` in a tracked folder was invisible while bash and zsh wrote `2-3`); the guide's Files
    sentence and its pin say the class the code refuses, a target the guard cannot read; the ledger entry corrects the
    clauses B2 made false and this decision's own privacy sentence above says so; the vendored skill names the two
    escalated false refusals and patch 0009 is regenerated; the rule's statement names the five-part predicate where it
    named a function befa93b3f removed; the corpus's `since` labels are swept against the passes' heads and pinned (one
    dropped, one re-anchored, one relabelled); the priced costs say what each shell does by execution; and every
    real-shell evidence leg, dash and bash included, goes through the one probe, which reports a shell that is missing or
    below the bash 4.3 floor with a `NOT RUN` line and whose `spawnSync` wrapper throws by name otherwise.
    Round 5's addendum (2026-09-20; five lenses over the round-5 commit, each running the hook as a process and every row
    unguarded in bash 5.2, zsh 5.9 and dash 0.5.12) closed what they found, every item a live false allow pre-existing at
    round 4's head or a claim no test held. THE FRAME LENS (a grammar-driven matrix of 3526 rows on four faces): a `{ }`
    group whose opening brace follows `&&`, `||` or `|` with its body on a later line was walked as a plain group while the
    shells skip it whole or run it in a subshell (36 rows in all three shells; `test -d d || {`, `mkdir d`, `cd d`, `}` and a
    relative write, the commonest multi-line conditional, was judged from d/); a group frame now carries the operator it
    was opened after (`openGroup`), `plainSequence` and the cd handler refuse through it, and a group behind `time` is
    marked too, since zsh does not keep an assignment standing alone in a timed group. The compound frame (`pushCompound`)
    records its body's opener, so a `{` before the opener is a brace body closed by its `}` (`compoundBody`, zsh's
    `if [[ .. ]] {`, `case x {`, `repeat n {`, `for y (..) {`, bash's `for y in ..; {` and `select ..; {`), a later segment
    after a word-list head or a `)` with nothing after it is zsh's one-command body that closes before the next segment
    (`oneSegment`, `closeOneSegment`), and a frame whose body was the frame pushed above it closes with it
    (`afterChildClosed`, `closeCompoundAt`); `BODY_CLOSER` holds the opener and the closer of every head and gains zsh's
    `repeat` and `foreach .. end`. A function body without braces (`f() cmd`, zsh and dash) is the one segment after the
    parentheses, defined and not run, where the frame had been popped and the body read as the enclosing scope's; every
    word before an empty pair of parentheses names a function (zsh's `f g () {`, `env f () {`) and every word after
    `function` up to its brace does (`function f g {`), bash rejecting each spelling; a `function NAME` whose brace opens
    on a later segment is run by dash, which has no `function` word, so a cd in it leaves the directory unknown
    (`popFunction`); `coproc` (bash and zsh) drops the word and its NAME and reads the rest inside a frame that keeps no
    name and restores the directory while its writes are judged, so `coproc cp base/report.md docs/report.md`, which the
    contract had listed among the unmodelled wrappers, is refused by name; and zsh's `always` continues a group. THE
    FREEZE LENS (163 constructs): the readonly skip ran before the scope check, so a bare `readonly x` in a body that may
    not run, a subshell, a pipeline, a piped or backgrounded group, after `&&` or `||` or in a function never called froze
    the guard's name and no shell's, and every shell performed the later write onto the tracked file (34 rows); `declare
    -r` and `typeset -r` freeze in bash and zsh and are not found in dash, which performs the write; `export -r`, `readonly
    -r`, `-x` and `-g` are options bash rejects, assigning nothing; an option after the operand is an operand to bash; and
    `local -r x` at the top level is rejected by bash. The freeze is now `!cmd.wrapped && seq.ok && cmd.name ===
    'readonly' && plainOptions` (an unwrapped `readonly` with no option word, a `--` before the operands aside, in plain
    sequence), a freeze made inside a group that turns out piped or backgrounded is undone at its brace, and every other
    road taints the name: the class widened to every `declare` and `typeset`, since dash has neither (`x=docs/report.md;
    declare x=scratch/keep.md; cp base/report.md $x` wrote the tracked file in dash, measured), and to any option word on
    `export` or `readonly`; `export NAME=..` and `readonly NAME=..` with no option word are the two declarations every
    shell performs, and `INERT_DECLARATION_FLAGS` is `ATTRIBUTE_ONLY_FLAGS`, a text table that picks the refusal's reason
    (a flag that changes the value, or the shells' disagreement) and changes no verdict. THE CENSUS LENS planted fourteen
    list shapes in scratch copies of the hook, each live on the write side, and twelve landed green: the census reads
    `var`, a declaration split after its `=` and spacing drift since, and names the six shapes it still cannot read (an
    inline literal at its point of use, a second declarator, a second `switch`, beside the call, string, regex-literal,
    later-filled `let` and in-function shapes it stated); the header's sentence that a planted list reds the test is
    qualified to the shapes the census reads; the writer cases stop at the switch's own `default:`; and the UNLISTED comment
    that said every scope row was a live false allow at round 4's head says nine of the ten (the subshell row was refused
    there) and that the select and subshell rows cover the table and the frame rather than the peel, with the population
    pinned (six mechanism rows, ten scope rows spelling each construct). THE MUTATION LENS found thirteen claims no test
    held; each is pinned (the assignment-only head read after the peel with a condition of assignments alone, the
    wrapper-word and assignment-word peels as refusals that cost nothing, the in-play check throwing inside the catch-all,
    the process-level catch on a removed working directory, the module-level `spawnSync` binding, the bash version floor
    by a stub, the runners' dropped shell default, the scan's list clause, the draw's population, the census side of
    `INTERPRETER_OPERANDS`, the priced-cost, privacy and `u`-letter sentences on the header and the ledger's two clauses)
    or stated in fork PR #780's body as unpinnable with the reason (the loop-variable read after the peel, held by the
    bare-mention rule; `Object.hasOwn` at the assignment-only head read, which no reserved-word head can be a prototype
    key of). THE DOCUMENTS LENS: the interpreter test's assertion that the untracked twin landed sits inside its bash leg,
    the prefix-script rows ask the probe for the inner bash they run, the catch count above says two rethrow and the
    process-level one refuses in place, the census method is named the same way here and on the header, and the corpus
    movement at c7d7505a9 was two readable rows and one cost row, three, 293 to 296, where the body had said four.
    Round 5's second addendum (2026-09-20; the round's verifier, driving the addendum's rows and rows of its own through the
    hook and unguarded in the three shells): two live false allows in zsh alone, both a `}` that shares a segment with the
    command before it. A brace body written on one line, `if (( 0 )) { cd ../scratch }; cp ../base/report.md report.md` from
    docs/ (the `for y ()`, `while`, `until`, `select`, `case a { b) .. }` and `for y in; { .. }` spellings the same), had
    `compoundBody` close its frame at the brace BEFORE the cd in the same segment was read, so the cd zsh skipped was followed
    and the write resolved to scratch/ while zsh wrote the tracked file; pre-existing at round 4's head and claimed closed by
    the addendum's F6 and F7, whose rows put the brace on its own segment. The brace is read after the segment's command now
    (`oneSegment`, the brace dropped from the words), so the cd makes the directory unknown at the close and an assignment in
    the body is unreadable with the body's own reason. And the trailing `}` of zsh's `{ cmd }` was read as the command's LAST
    OPERAND, the destination of cp, mv, install and ln, so `{ cp ../base/report.md report.md }` (in a plain group, a `then` or
    `do` body, a function body, a group after `&&`) read the tracked file as a source and was allowed while zsh performed it:
    every writer is judged with the trailing braces and without them (`variants`), a write under either reading refused. The
    one new cost is the priced class's zsh one-line spelling (`if (( 1 )) { cd .. }`, `for y (a) { cd .. }`, refused as an
    unknown directory like `if true; then cd ..; fi`), priced in the corpus. Beside them: the census reads a declaration with
    any spacing after its keyword (`const  NAME = ..` was not enumerated and not among the stated blind spots), and the
    vendored README's row for patch 0009 states the addendum's declaration rule the right way round (no declaration flag and
    no `declare`, `typeset` or `local` keeps a name readable, nor does a group opened after `&&`, `||` or `|`; the row had
    said they keep it readable).
    Round 5's third addendum (2026-09-20; the round's verifier, on the second addendum's head): twenty live false allows in
    the family that addendum claimed closed, a `}` sharing a segment with the words before it, in the frames its fix did not
    reach. The function-body scan (`braces`) popped its frame at the brace before the cd sharing the segment was read, so
    `f() { cd ../scratch }; cp ../base/report.md report.md` from docs/ followed the cd as plain sequence and was allowed while
    zsh wrote docs/report.md, in thirteen spellings (`function f { .. }`, which dash runs too, `function f() { .. }`, `f g ()
    { .. }`, `! f() { .. }`, nested, two commands, a newline, an `&&` join, a redirect after the brace, a quoted operand,
    pushd, a group holding the definition); after `compoundBody` spliced a shared-segment brace, the words after it (`else {
    .. }`, `always { .. }`, a while's condition group) became operands of the body's command, so `if (( 1 )) { cp .. } else {
    : }`, `if (( 0 )) { : } else { cp .. }`, `{ cp .. } always { : }`, `{ : } always { cp .. }` and `while { cp .. } { break
    }` were allowed while zsh copied; and `repeat 1 { cp .. }` read the brace body as repeat's operands. So the second
    addendum's claims above, the operand face closed in a plain group, a `then` or `do` body, a function body and a group
    after `&&`, and the cd face closed for every head of `BODY_CLOSER`, were false while those were live. THE RULE, stated
    once at the lexer (`splitAtClosers`) and read by every frame kind through the segments it produces: an unquoted `}` that
    follows other words in its segment ends its construct only after those words are read as the construct's own command,
    and every word after it begins a new command; the lexer cuts the segment before such a brace, so a compound body, a
    condition group, a function body, a plain group, a repeat body and the `else`, `elif` and `always` continuations each
    read a one-line brace form as its `;` twin, through the code they had, and no frame kind carries a reading of its own.
    Beside the cut: `compoundBody` keeps an `if` frame open across `else` and `elif` on the closer's segment, reads a `{`
    first after `if`, `while` or `until` with no `(( ))` between (`arithAt`, recorded by the lexer) as a condition group whose
    `}` leaves the frame waiting for its body, reads zsh's one-command body after `))`, `]]` or a condition group's `}` (`if
    (( 0 )) cd ../scratch; cp ..` had walked the skipped cd as plain sequence), and drops a condition's words before the body
    so `commandOf` reads the body's command (`if [[ 1 = 1 ]] { cp .. }` had read `[[` as the command and the copy as its
    operand); the head branch drops `repeat N` before either body form; `braces` reads from the index a compound closer
    handed it and stops at a compound head inside the body; and a closer segment's redirections are judged in the directory
    saved when its construct opened (`closedConstruct`, `addRedirects`), since every shell opens them before the construct
    runs (`{ cd ../scratch; } > report.md` and `if true; then cd ../scratch; fi > report.md` from docs/ truncated
    docs/report.md in bash, zsh and dash while the guard judged the target after the cd it had followed inside). Gone with
    it: the second addendum's `oneSegment` splice and its trailing-brace cut at the writer (the cut braces travel on the
    segment as `closerTail`, so a writer is still judged with them as operands, bash's and dash's reading of `cp a }`), the
    group scan's `always` splice (the lexer drops `} always {`: one group, closed by the last brace) and the seventh pass's
    `pendingClose`. The cost: a condition group's cd (`if { cd ../scratch } { : }`, which zsh runs) is read as a body's and
    the directory after it is unknown, the class `if true; then cd ..; fi` prices, one corpus row. Pinned with the verifier's
    twenty rows and the rows found beside them, each run through the hook as a process and unguarded in the three shells with
    the writers asserted, and with a generated matrix over frame kind, brace placement, face and position whose rows are the
    pin (a row a shell writes must refuse; the refusals where no shell writes are counted and listed as the cost): 2912 rows,
    2845 refused, 67 allowed, 0 a shell writes while the hook allows (213 at the second addendum's head), 470 spellings no
    shell parses, 955 refusals of a face in a body no shell runs (the standing rules), 182 of the priced classes (88 a cd in a
    construct that runs, 88 an assignment there, 6 a writer in a piped definition whose call finds no function), the fixture
    `tools/romp-track-bash-guard-brace-matrix.json` beside the test.
    Round 5's fourth addendum (2026-09-20; the round's verifier, on the third addendum's head): the function body's count
    (`braces`) read a quoted brace word as a brace of the body, against the rule's own text, so `f() { echo "}"; cd
    ../scratch; }; cp ../base/report.md report.md` from docs/ popped the frame at the quoted word, followed the cd as plain
    sequence and was allowed while bash, zsh and dash wrote docs/report.md (present at round 4's head), and the census of
    the hook's brace reads found the same gap in the reserved-word reads that hold `{` and `}` (the lexer took `[[` after
    any word spelled as a reserved word for the test keyword, so `echo "{" [[ x > report.md ]]` was allowed while bash and
    dash redirected; `commandOf` and `rawHeadIndexOf` skipped a quoted reserved word, so `"{" cd ../scratch; cp ..` followed
    a cd that was the operand of a command named `{`), so every brace read checks `plainWord` now, pinned with the
    verifier's rows in bash, zsh and dash by execution and five matrix kinds (3152 rows, 3065 refused, 87 allowed, 0 a shell
    writes while the hook allows, the 2912 rows before unchanged).
    Round 5's fifth addendum (2026-09-20; the fourth addendum's builder measured it, and the reviewer ruled it fixed before
    the round): `[[ x > report.md ]]` from docs/, alone, in an if or in a group, was allowed while dash, which has no `[[`,
    ran a command named so and performed the redirection (writers=[dash]); the hook read the test under bash and zsh
    grammar, where a `>` between `[[` and `]]` compares. The reviewer's rule: a construct must be read on the safe side for
    every shell the guard claims (bash, zsh and dash), not for the grammar it was written against. THE RULE, stated once at
    the lexer's `closeTest` and read here in the same words: a construct the hook reads under bash and zsh grammar (`[[ ... ]]`, `(( ... ))`, a `$(( ... ))`) contributes, in addition, its dash reading to the write set: where dash reads the construct as a plain command (`[[`), the words after the head are its operands and every redirection operator among them a redirection dash performs before the command is looked up, and the words after a `&&` or `||` among them a further command; where dash reads it as a subshell (`((`, two nested `(`), its body is a command list dash runs; and each target so found is judged exactly as any redirection or writer the hook already judges. Beside it: a substitution inside an arithmetic body (`$(...)`, a backtick) runs in every shell and is read as a command, and a `$((` whose first `(` closes before the last is a command substitution in bash and zsh and is read as one. The derivation over the lexer's non-redirecting reads (every path where a `>`, `>>`, `&>`, `>|` or `<>` is read as
    something other than a redirection, by execution in bash 5.2, zsh 5.9 and dash 0.5.12): the `[[ ]]` comparison (a
    command in dash: `closeTest`, the dash pieces spliced into the walk by `withDashPieces`, a cd there an unknown
    directory and an assignment there unreadable, as after any `||`); the `(( ))` arithmetic (a subshell in dash, its body
    a command list, `skipArithmetic` and `viaSubs`; `(( cp a b ))` copies in dash); the `$(( ))` expansion (arithmetic in
    dash, `$( (` in bash and zsh when its first `(` closes before the last, `parenCloseAt`; `echo $((x > report.md);(y))`
    truncated the file in both); the substitutions inside any arithmetic body (never read before; `(( $(echo x >
    report.md) ))` wrote in all three, `for (( i=$(..); .. ))` in bash and zsh, `expansionsOf`); and the reads that diverge
    in no way that writes (a here-doc body is data in all three once expanded, its expansions performed alike and read since the
    third fix-up; a here-string and a process substitution are syntax
    errors in dash, though bash performs a process substitution inside `[[ ]]` (the fix-up below); quotes read alike; a brace list dash writes as one literal name, `{a,b}.md`, a residual named below).
    Where dash parses nothing, no dash reading is due, measured: a `for (( ))` head ("Bad for loop variable"), a `((`
    after any word but a reserved one (`time ((`, `echo ((`, `x=1 ((`, `} ((`), an unquoted parenthesis between `[[` and
    `]]`. The shell facts live in `TEST_ARITH_SHELLS` (bash, zsh and ksh read the test keyword and arithmetic; a script
    handed to dash or `sh` takes the dash reading, one handed to bash the test alone: `dash -c '[[ x > report.md ]]'` was
    allowed while every shell spawned dash and wrote) and `CONSTRUCT_HEADS` (each construct's closer, both readings and
    the text the refusal appends to the write's `how`, so a refusal names dash and the construct). The reserved-word
    derivation ran every word of `RESERVED`, `BODY_CLOSER`, its closers and openers, `function`, `coproc`, `always`,
    `time`, `[[`, `]]`, `((` and `))`, quoted and unquoted, with a `>` operand and a writer operand, through the hook and
    the three shells (112 rows): the two constructs, unquoted, were the only rows a shell wrote that the hook allowed; the
    change turns those three rows to refusals and no other. THE COSTS, each measured with no shell writing: `[[ $a > $b ]]`
    with `$b` unreadable from a tracked cwd is refused as not literal (the non-literal rule for a redirection target; the
    refusal adds the comparison's remedy, `expr` or a directory outside the project; a `$b` the command set to a plain
    string resolves and is judged by its value); the words after a `&&` inside the test (dash skips them when `[[` is not
    found, and they are read as running since a command named `[[` on PATH would run them); `>>` and `<>` onto an
    existing tracked file through a command that is not found (the operator opens the file and writes no byte; the same
    spelling onto a name that does not exist yet under a tracked folder creates it, measured); and the dead spellings no
    shell parses (`} (( x > report.md ))`). THE CONSTRUCT MATRIX (`tools/romp-track-bash-guard-construct-matrix.json`,
    its population stated in the fixture: head, from `CONSTRUCT_HEADS`'s command-position entries, x twelve positions x
    seven operator forms x three targets, 456 rows, run through the hook as a process and unguarded in the three shells):
    456 rows, 299 refused, 157 allowed, dash the only writer (200 rows), 0 a shell writes while the hook allows; the
    refusals where no shell writes by class: 13 dead, 26 a definition never called, 40 the append or read-write operator
    onto the existing file, 20 the unset name, 0 other. The brace matrix's 3152 rows are unchanged by the change (its
    fixture now states its population, which has no `>` inside a test or arithmetic). OUTSIDE BOTH POPULATIONS, named: a
    construct nested in a construct, a target through `~`, a glob or a brace list inside a construct, a construct inside a
    script beyond the three `-c` rows, every position the twelve do not spell (a case or select body, zsh's brace bodies, a
    coproc), and dash's literal reading of a brace list (`> docs/{a,b}.md` writes `docs/{a,b}.md` in dash: judged only when
    an alternative is tracked).
    THE FIX-UP (2026-09-20; the addendum's verifier, on its head): two reads at the test's boundaries failed toward allowing,
    both inside the addendum's own construct and both present at the fourth addendum's head too. A process substitution
    among the operands was read as the test's `<` and a `(`, the test's own operators being read before the expansion, so
    `[[ -f <(echo x > report.md) ]]` from docs/ was allowed while bash performed it and wrote, in every position (alone,
    `!`, if, while, a group, a called function, after `&&`, inside `$(...)`; through `bash -c` and a heredoc-fed bash every
    shell wrote; zsh performs it after `!`, in a pipeline, with `&`, `|&` and under coproc, and rejects it alone, in `( )`, in a
    group, in if, in a called function, in `$(...)` and via `zsh -c`; dash rejects it as a syntax error; the addendum's
    own row had measured the substitution outside a test only). An operator glued to the closing `]]` was read as a word
    of the test, the operator read running before the `]]` under way had ended the word, so `[[ a ]]>report.md`,
    `[[ a ]]>|report.md`, `[[ -n a ]]&&cp ../base/report.md report.md`, `[[ -z a ]]||cp ..` and `[[ -z a ]]||cd ..; cp
    base/report.md docs/report.md` were allowed while bash, zsh and dash wrote (`>>`, `<>`, `2>` and `&>` glued were
    refused by accident, their second character reaching the ordinary path). The two families' 42 rows through the hook
    as a process from docs/ and the three shells, before the change: `rows 42 refused 8 allowed 34 other 0 writes bash=39
    zsh=23 dash=20 timeouts 0`, `FALSE ALLOWS (allowed, a shell writes): 34`; after: `rows 42 refused 42 allowed 0 other 0
    writes bash=39 zsh=23 dash=20 timeouts 0`, `FALSE ALLOWS (allowed, a shell writes): 0`. THE TEST'S BOUNDARIES, stated
    beside the rule at the lexer and here in the same words: the test's grammar covers the words between `[[` and the
    unquoted `]]` that closes it and only the test's own operators among them; an expansion among the operands (a
    `$(...)`, a backtick, a `<(...)` or `>(...)`) is performed by the shell before the test reads a word and is read as the
    command it runs, where it is lexed; and an operator glued to the closing `]]` is outside the test, the redirection or
    list operator it is anywhere else, read after the test has closed. Both are made at the lexer's operator read (the
    `]]` under way ends the test first; `<(` and `>(` are read before the test's own `<` and `>`, under the test grammar
    alone, since dash reads them as `<` and an unquoted `(`, the syntax error `closeTest` already reads as no dash
    reading), so they hold in every position. THE POPULATION, widened by the property the verifier named: the construct
    matrix crosses the PLACEMENT of the write against the construct with head, position, operator and target, the
    placements being the regions a construct has (before the head is the position; among the operands; inside an
    expansion among the operands, a `$(...)` in every shell and a `<(...)` in bash; after the closer, glued or spaced):
    five placements, 2280 rows, through the hook as a process and unguarded in the three shells: `rows 2280 refused 1547
    allowed 733 other 0 writes bash=741 zsh=653 dash=820 timeouts 0`, `FALSE ALLOWS (allowed, a shell writes): 0`; the
    addendum's 456 rows are the operand placement, `existing rows: 456 unchanged, 0 changed`; the refusals where no shell
    writes by class: `dead 91 doctrine 130 opens 173 unset 102 arith-procsub 110 other 0` (arith-procsub: a process
    substitution as an operand of `(( ))`, an arithmetic error in bash and zsh and a syntax error in dash, the expansion
    read as the command a shell would run). Outside it still: the `$((` family, a backtick among the operands (the path a
    `$(...)` takes), the further commands after `&&` or `||` inside the test, nested constructs, `~`, glob and brace
    targets, scripts beyond the `-c` rows, positions beyond the twelve, and a redirection before the head or with a
    descriptor number (the rows test pins `2>` glued and a triple `]]]`, dash's operand and redirection). THE COSTS,
    each measured with no shell writing: `[[ -f <(echo x > $n) ]]` and `[[ a ]]>$n` with `$n` unset (the non-literal
    rule; bash reports an ambiguous redirect); `(( <(echo x > report.md) ))` (an arithmetic error in bash and zsh, dash's
    syntax error; the body's expansion read as a command); `[[ -f <([[ x > report.md ]]) ]]` (the inner test's dash
    reading inside a substitution dash never performs); `dash -c '[[ -f <(echo x > report.md) ]]'` (dash's `<` and `(`, a
    subshell running the echo in the hook's reading, a syntax error in dash); and `[[ a ]]>>report.md` and
    `[[ a ]]<>report.md` (the test prints nothing: the operator opens the file and writes no byte, where the notes/ twin
    creates its file). One verdict widened toward allowing: `dash -c 'tee >(cat) report.md'`, refused before under the
    bash reading of a dash script, allowed now, dash rejecting `>(` and running nothing (measured, every shell spawning
    dash). The twins stay allowed: `[[ -f <(echo x > ../scratch/keep.md) ]]`, `[[ a ]]>../scratch/keep.md`,
    `[[ -f <(cat report.md) ]]`, `[[ -f <(true) || cp ../base/report.md report.md ]]` (a syntax error in every shell,
    dash's reading seeing the parenthesis), `[[ a ]]<report.md`, and `[[ a ]]>report.md]]` (the target `report.md]]`,
    untracked, in every shell). Pinned: the rows test's group (11), 61 rows (the two families, the twins, the costs), the
    construct matrix's fixture with its placement dimension, the lexer's three reads in their order (the plan test), and
    the shapes tests' targets and hook-process rows.
    THE SECOND FIX-UP (2026-09-20; the fix-up's verifiers, on its head): two more reads failing toward allowing, each a class,
    one at the lexer and one present since the guard's first commit. (1) THE NESTED EXPANSION: a `$(...)`, a backtick or a
    `<(...)` inside a `${...}` word was never lexed (the `${` read skipped its inner text whole), so `echo ${x:-$(cp
    ../base/report.md report.md)}` from docs/ was `ALLOWED writers=[bash,zsh,dash]`, and so were `${x-..}`, `${x:=..}`, the
    double-quoted word, the backtick, `${x:-${y:-..}}`, `[[ -n ${x:-$(echo x > report.md)} ]]`, `(( ${x:-$(echo x >
    report.md; echo 1)} ))` and `dash -c 'echo ${x:-$(cp ..)}'` (`writers=[bash,zsh,dash]`), `${x:?..}`
    (`writers=[bash,dash]`), `${x[$(..)]}` (`writers=[bash,zsh]`), `${x#..}` and `${x/b/..}` with x unset (`writers=[zsh]`;
    with x set every shell but dash's `/`), `[[ -n ${x:-<(echo x > report.md)} ]]` and `cat ${x:-<(echo x > report.md)}`
    (`writers=[bash]`), and the same from notes/, the project root and out/; the verifiers' 21 param-word rows and the three
    `${...}`-as-target rows (W31 to W33, refused by the non-literal rule before and still) through the hook as a process from
    each row's cwd with ROMP_SID set, then bash 5.2, zsh 5.9 and dash 0.5.12 unguarded over a fresh world (the shells the
    guard claims; busybox sh and ash are outside them and outside every count here), before: `rows 24 refused 3 allowed 21
    other 0 writes bash=21 zsh=20 dash=18 timeouts 0`, `FALSE ALLOWS (allowed, a shell writes): 20` (the 24 rows; the one
    param-word row no shell writes is `${x:+..}` with x unset); after: `rows 24 refused 24 allowed 0 other 0 writes bash=21
    zsh=20 dash=18 timeouts 0`, `FALSE ALLOWS (allowed, a shell writes): 0`. THE RULE, stated at the lexer's `nestedExpansions`
    and here in the same words: an expansion nested inside a parameter-expansion word is read as the command it runs, recursively, in every position (an operand, inside `[[ ]]`, inside `(( ))`, a redirection target, a quoted word), exactly as an expansion among plain operands is read; the `${` read descends. The inner text is lexed with the same lexer under the same shell, with
    no comment (a `#` is a character there: `${x:-a #$(cmd)}` runs cmd in every shell, measured) and in the quoting the word
    stands in (inside double quotes a single quote is a character, `"${x:-'$(cmd)'}"` runs cmd in every shell where the
    unquoted `${x:-'$(cmd)'}` runs nothing; a `<(` is read in both quotings, since bash performs it unquoted anywhere in the
    word and double-quoted in the pattern, replacement and message parts, `"${x#<(cmd)}"`, `"${x/b/<(cmd)}"`, `"${x:?<(cmd)}"`,
    each measured writing; a backslash escapes the dollar in both), and every substitution it finds joins the segment's
    `viaSubs` with the word named (`BRACE_WORD_VIA`), where the walk reads it as any `$(...)` of the command; the `${...}` word
    itself keeps the non-literal rule. The skip over the brace's inner text (`skipNested`) reads a `$(...)` inside a `${...}`, a
    `${...}` inside a `$(...)` and a backtick inside either as the units the shells parse, so a closer inside them is their own
    (`${x:-$(echo } > report.md)}` runs the echo in bash and dash, a parse error in zsh), and a single quote is a character in a
    double-quoted brace, as the shells read it. (2) THE PIPED SCRIPT: `echo 'cp ../base/report.md report.md' | bash`, `echo
    'echo x > report.md' | sh`, `echo '[[ x > report.md ]]' | dash`, `printf '%s\n' '[[ a ]]>report.md' | bash`, from docs/,
    notes/ and the project root, through `bash -s`, `sh -` and the double-quoted script, were `ALLOWED
    writers=[bash,zsh,dash]`: the heredoc-fed shell (`bash <<EOF`, `bash -s`, `sh -`, `cat <<'EOF' | bash`) and the
    here-string were read as `sh -c` is, a pipe from echo or printf appeared neither as read nor as a residual. The 13 rows
    (the verifiers' spellings, the heredoc and here-string twins, a `cat f` and a `"$s"` producer) before: `rows 13 refused 2
    allowed 11 other 0 writes bash=12 zsh=12 dash=11 timeouts 0`, `FALSE ALLOWS (allowed, a shell writes): 10`; after: `rows
    13 refused 11 allowed 2 other 0 writes bash=12 zsh=12 dash=11 timeouts 0`, `FALSE ALLOWS (allowed, a shell writes): 1`
    (the 13 rows; the one is `s='cp ..'; echo "$s" | bash`, the residual below). THE RULE, stated at extract's `stdinBodies`
    (`pipedScripts`, `echoOutput`, `printfOutput`, `shellEscapes`) and here in the same words: when a pipeline's last command is a shell of SHELLS reading its script from stdin (no `-c`, no script operand: `bash`, `bash -s`, `sh -`, dash) and the command piped into it is an echo or a printf, the words echo or printf would print are the script, read as the here-string form already is, under the grammar the shell named uses (dash's for `sh` and `dash`, TEST_ARITH_SHELLS); each
    word as the lexer read it, so a quoted script is literal and an expansion in it keeps its spelling and takes the
    non-literal rules, as a here-string's does. echo's output is read once as spelled and once with the escapes interpreted
    (bash's default and its `-e`, zsh's and dash's default), its leading option words dropped (dash prints them, a reading
    whose writes the stripped one covers); printf's format has its escapes interpreted and its conversions take the operands
    in order, `%b` with escapes, the format reused while operands remain, `-v` printing nothing. THE RESIDUAL, named here and
    on the hook header beside the heredoc-fed forms: a producer the guard cannot see stays unread and its script passes (`cat f
    | bash`; `s='cp ..'; echo "$s" | bash`, since a value with whitespace is never resolved, the readability rule, exactly as
    `bash <<< "$s"` is not read; a tee, a subshell, a group or a function before the pipe), and so does a script handed to a
    shell outside `SHELLS` (busybox `sh` or `ash`: `busybox sh -c 'cp ../base/report.md report.md'`, `busybox ash -c '[[ x >
    report.md ]]'`, whose `[[` is a builtin performing the redirection, and `echo 'cp ..' | busybox sh` each `ALLOWED
    writers=[bash,zsh,dash]`, measured; eval and xargs the same, as named before); the rows test pins each allowed, so a
    residual the guard starts reading shows as a rule to state. THE POPULATIONS, each through the hook as a process from the
    row's cwd and the three shells unguarded, the fixtures stating them: the param-word matrix
    (`tools/romp-track-bash-guard-param-word-matrix.json`: 17 operator forms x 3 nested expansions x 5 positions x 4 cwds),
    `rows 1020 refused 1020 allowed 0 other 0 writes bash=936 zsh=608 dash=572 timeouts 0`, `FALSE ALLOWS (allowed, a shell
    writes; the 1020 rows not marked residual): 0`, `refused with no writer: arith-procsub 32 quoted-procsub 32
    subscript-procsub 20` (its first run, with a double-quoted `<(` still read as text, printed `FALSE ALLOWS 32`, the pattern,
    replacement and message forms bash performs: the matrix's own find, folded in before the fixture was written); the
    piped-script matrix (`tools/romp-track-bash-guard-piped-script-matrix.json`: 3 producers x 2 quotings x 3 scripts x the 5
    shells of SHELLS x 3 forms, plus 6 residual producers x 5 consumers), `rows 300 refused 216 allowed 84 other 0 writes
    bash=200 zsh=200 dash=200 timeouts 0`, `FALSE ALLOWS (allowed, a shell writes; the 270 rows not marked residual): 0`,
    `residual rows 30, refused 0; residual rows a shell writes: 20`, `refused with no writer: absent 36` (ksh is not installed
    here). THE COSTS, each measured with no shell writing: the word's command is read whatever the parameter's state (`x=1;
    echo ${x:-$(cp ..)}`, `${x:+$(cp ..)}` with x unset); a double-quoted `<(...)` in the `:-` family (`"${x:-<(cp ..)}"`,
    32 matrix rows); a `<(...)` as a subscript (`${x[<(cp ..)]}`, a syntax error in bash, a bad math expression in zsh, a bad
    substitution in dash, 20 rows); a `<(...)` inside a `${...}` operand of `(( ))` (an arithmetic error in bash and zsh, a
    syntax error in dash, 32 rows); a script piped into a consumer that is not installed (ksh, 36 rows); and an expansion in a
    piped script (`echo 'cp ../base/report.md' $t | bash`: the non-literal rule, while bash's copy fails on one operand). The
    verdicts of the addendum's and the fix-up's fixtures are unchanged (`existing rows: 2280 unchanged, 0 changed, 0
    missing` for the construct matrix at this commit). Pinned: the rows test's second fix-up group (79 rows: the verifiers'
    rows with exact writers, W31 to W34, the quoting corners, the costs, the piped forms, the residuals, the heredoc twins), the
    two matrix fixtures, the lexer's descent and the piped script in-process, and the plan test (both rules on both surfaces in
    the same words, the functions, the fixtures' populations, the residual named on the header, here and hooks/README.md).
    Mutation on scratch copies: with the `${` descent removed, the verifiers' rows print `FALSE ALLOWS (allowed, a shell
    writes): 20` and the param-word matrix and the rows tests go red (`the param-word matrix: no row a shell writes is
    allowed`, `P-colon-minus: refused`); with the piped-script read removed, `FALSE ALLOWS (allowed, a shell writes): 10` and
    the piped-script matrix and the rows tests go red (`the piped-script matrix: no row a shell writes is allowed`,
    `S-echo-bash: refused`).
    THE THIRD FIX-UP (2026-09-20; the second fix-up's two verifiers, on its head): seven live classes, each present at the pushed
    head, four of them written by bash, zsh and dash, and three more found while pinning them, every one reproduced by execution
    before the code changed (the hook as a process from the synthetic project's docs/, notes/, the project root and out/ with
    ROMP_SID set, then bash 5.2, zsh 5.9 and dash 0.5.12 unguarded over a fresh world, the tracked subset fingerprinted before and
    after; busybox sh and ash are outside the claimed shells and outside every count here). THE VERIFIERS' ROWS (274, their own
    spellings, the same harness) at the second fix-up's head: `SUMMARY rows 274 refused 224 allowed 50 other 0 writes bash=243
    zsh=235 dash=193 busybox=229 timeouts 0`, `FALSE ALLOWS (allowed, one of bash/zsh/dash writes): 45`; at this commit: `SUMMARY
    rows 274 refused 244 allowed 30 other 0 writes bash=243 zsh=235 dash=193 busybox=229 timeouts 0`, `FALSE ALLOWS (allowed, one of
    bash/zsh/dash writes): 25`, the 25 the residuals named here and before (a command whose name is an expansion, `${SHELL} -c
    '..'`, `echo '..' | $SHELL`, 15 rows; a producer the guard cannot read, `| tee /dev/null | bash`, `| sed '' | bash`, `| cat |
    bash`, `"$s" | bash`, `yes '..' | head -1 | bash`, 6 rows; a script written to a file and run, 2 rows; eval, 1 row; zsh's
    `${(e)x}`, the eval class, 1 row), `COSTS (refused, no claimed shell writes): 11` before and after, 20 verdicts changed, each
    from allowed to refused. (1) THE UNQUOTED BODY: `cat <<EOF` with `$(cp ../base/report.md report.md)` on the body's line, and
    with `${x:-$(cp ..)}`, from docs/ were `ALLOWED writers=[bash,zsh,dash]`: the body was kept as the consumer's data and never
    lexed, though every shell performs its expansions before any consumer reads it (measured: the backtick, `<<-`, `<< EOF`, from
    notes/ and out/, a python consumer, and the quote as a character in the body, `${x:-'$(cp ..)'}`, each writing in all three;
    `<<'EOF'`, `<<"EOF"`, `<<\EOF`, `<<E"O"F` and the escaped `\$(` writing in none). THE RULE, stated at `readHeredocBodies` in
    the lexer and here in the same words: a here-document whose delimiter has no quoted character has its body expanded by the shell before the command reads it, so a `$(...)`, a backtick, a `${...}` and a `$name` in the body are read as they are anywhere else and the body the consumer reads is the text after those expansions; a delimiter with any quoted character keeps the body as written and runs nothing. The expanded body is the consumer's stdin text, so a shell fed by it reads
    the script the shell will run: `bash <<EOF` with `$(echo 'echo x > report.md')` on a line wrote report.md in all three (the
    printed text parsed as a redirection) while the same body after `<<'EOF'` runs the echo and prints; `<<'EOF'` with `$(echo 'cp
    ..')` copies in all three (bash splits the printed text and runs it), read as any script. (2) THE RESOLVED SUBSTITUTION: `bash
    -c "$(echo 'cp ../base/report.md report.md')"`, `bash <<< "$(echo '..')"`, that line inside a here-document fed to bash and
    `echo "$(echo '..')" | bash` from docs/ were `ALLOWED writers=[bash,zsh,dash]` (`writers=[bash,zsh]` for the here-string, which
    dash rejects): the `$(...)` was read as the command it runs, an echo that writes nothing, and the text it prints, which the
    guard could see, was never the script. THE RULE, stated at `resolvedSub` in the lexer (`literalOutput` reads the command) and
    here in the same words: a `$(...)` or a backtick whose command is one echo or printf with literal operands and no redirection prints text the guard can see, and that text stands in the word where the shell puts it, whole where no shell splits an expansion's result (inside double quotes, as a here-string, in a here-document body, as the word of a `${...}` operator), split at blanks into the words the shell makes among unquoted operands, and at a redirection target both, the whole text as dash opens it and each blank-separated field as zsh opens it (bash opens the one field, or none of several), each a redirection of its own, so the word is literal and a script it forms is read as the here-string form already is; when echo's two readings differ, a word that is the substitution alone keeps both texts and a script formed from it is read under each. Measured: `bash -c "$(echo 'echo x > report.md')"` writes in all three; `$(echo cp)
    ../base/report.md report.md` and the substitution alone as the command line copy in all three, split into the words the shell
    runs; `x=$(echo 'report.md'); cp ../base/report.md $x` copies in all three (the value resolves); `bash -c $(echo 'cp a b')`,
    split, hands `cp` alone to bash and `"$(echo 'cp a b')"` is a command named so (no shell writes: both allowed); `bash -c
    "$(echo 'cp a b\c')"` copies in zsh and dash and not in bash (`writers=[zsh,dash]`, the two readings), `echo -e` in bash and
    zsh (dash's echo prints the `-e`, which bash rejects); `sed -i .. $(echo '*.md')` rewrites in bash and dash (the glob) and not
    in zsh; `> $(echo '{a,b}.md')` writes the literal name in all three (no brace list); `IFS=:; cp $(echo 'a:b')` is not resolved
    (the split follows a rule the guard does not read) and takes THE SPLIT OPERAND below. The text carries the mark 'e' (`isGlobMark`):
    unquoted for a glob, never a brace list, never a reserved word. (3) THE DEFAULT WORD (found while reproducing the verifiers'
    rows): `bash -c "${x:-$(echo 'cp ../base/report.md report.md')}"` from docs/ was `ALLOWED writers=[bash,zsh,dash]`, the `${...}`
    word the residual "a script held in a variable" while its word was text the guard could read. THE RULE, stated at
    `defaultReading` in the lexer (from the same descent as `nestedExpansions`: a second lex per level was exponential in the
    nesting, the cap test's 70 levels never returning) and here in the same words: `${name:-word}`, `${name-word}`, `${name:=word}` and `${name=word}` stand for word when the name is unset, and `${name:+word}` and `${name+word}` when it is set, so when word lexes to one literal text under the word's quoting that text is a reading of the word, read as a script where the word is one (a `-c` operand, a here-string, a here-document body fed to a shell), in every position, since zsh splits no expansion's result. Measured: `bash -c ${x:-'cp a
    b'}` unquoted copies in all three (the quotes quote) and `bash -c "${x:-'cp a b'}"` in none (inside double quotes the quotes are
    characters: a command named `cp a b`); `bash -c "${x:-cp a b}"` copies in all three and `bash -c ${x:-cp a b}` unquoted in zsh
    alone (bash and dash split the word and hand `cp` alone to bash); `${x-..}`, `${x:=..}` and `${x:+..}` with x set copy in all
    three; `${x:?..}` (a message) and `${x}` give no reading; in a here-document body `${x:-'cp a b'}` runs nothing (the quotes are
    characters there too). (4) ZSH'S `=(cmd)`: `echo ${x:-=(cp ../base/report.md report.md)}` from docs/ was `ALLOWED writers=[zsh]`,
    `=(` appearing nowhere in the hook, while the bare `cat =(cp ..)` and `: =(cp ..)` were refused by accident (the parenthesis read
    as a subshell). THE RULE, stated at `eqProcsubStart` in the lexer and here in the same words: zsh performs `=(cmd)` where a word begins, unquoted (an operand, an assignment's value, the word of a `${...}` operator, a replacement part), and nowhere else, so it is read as `<(cmd)` is, cmd running and read like a `$(...)`, for the Bash tool's command and for a script handed to zsh. Measured writing in
    zsh: the operand, `x==(cp ..)`, `${x:-=(..)}`, `${x:-${y:-=(..)}}`, `${(e)x:-=(..)}`, `${x/b/=(..)}`, `zsh =(echo 'cp ..')` as a
    script operand; writing in none: `${x:-a=(..)}`, `[[ -n =(..) ]]`, `"${x:-=(..)}"`, `${x:-"=(..)"}`, `bash -c 'cat =(..)'` (a
    syntax error in bash, whose parenthesis the guard still reads as a subshell, a cost that predates this fix-up), `x=abc; echo
    ${x#=(..)}` (read all the same, a priced cost). (5) THE CONSUMER'S STDIN: `echo 'cp ../base/report.md report.md' | (bash)`, `|
    if true; then bash; fi`, `| bash /dev/stdin`, `| bash /dev/fd/0`, `| bash -c 'bash'`, `| sh -c sh`, `| bash -c 'exec bash'` and
    `| bash -c 'bash -s'` from docs/ were `ALLOWED writers=[bash,zsh,dash]`, `bash <(echo '..')`, `bash < <(echo '..')` and `bash -s
    < <(echo '..')` `ALLOWED writers=[bash,zsh]`, while `| { bash; }` was refused by accident (the brace sharing the shell's
    segment); found beside them, `(bash) <<'EOF'`, `{ bash; } <<'EOF'` and `if true; then bash; fi <<'EOF'` with the copy in the
    body, `ALLOWED writers=[bash,zsh,dash]`. THE RULE, stated at extract's `stdinBodies` (`producerAt` through the frames'
    `stdinFrom`, `closerStdin` into their `stdinText`, THE INHERITED STDIN in `recurse`, `STDIN_NAMES` in `shellScript` and the
    interpreter walk, `procsubOf` and `literalOutput` for the substitution) and here in the same words: a compound command's standard input is the pipeline's, and so is what a redirection on its closer feeds it, so every command inside it that reads its script from stdin reads what was piped into the compound or redirected onto its closer; a `<` into the standard input feeds the command what it names, read when it is a process substitution whose command is a literal echo or printf, as a script operand that is one is read; a script operand naming the standard input (`-`, `/dev/stdin`, `/dev/fd/0`, `/proc/self/fd/0`) reads it; and a `-c` script, a `$(...)` and a script the shell reads from a file run with their caller's standard input. Measured:
    every compound kind, the nesting, a here-string and a `<(echo ..)` on the closer, `bash 3</dev/null` (the pipe still read) and
    `echo '..' | bash </dev/null` (zsh's multios feeds the pipe too: `writers=[zsh]`, both read); a definition (`| f() { bash; }`)
    reads nothing; the costs, refused with no shell writing: `| while read -r l; do bash; done` and `| bash -c 'cat; bash'` (the
    input drained before the shell), `| if true; then :; else bash; fi` (the branch not taken), `bash <(cat f)` allowed (a producer
    the guard cannot read, the residual). (6) THE SPLIT OPERAND (found while pinning the IFS cost): `IFS=:; cp $(echo
    '../base/report.md:report.md')` from docs/ was `ALLOWED writers=[bash,zsh,dash]`, `cp $1` and `cp $(cat f)` the same shape, a
    form present since the guard's first commit: a writer with fewer operands than it needs named no target. THE RULE, stated at the
    copying writers' case in extract and here in the same words: when a copying writer (cp, mv, install, ln) has fewer operands than its two and one of them is an unquoted expansion the guard did not resolve, the shell may split it into the operands the writer needs, so that operand is a target the hook cannot read (`cp "$(cat f)"`, double-quoted, never splits and
    stays allowed). THE POPULATIONS, each through the hook as a process from the row's cwd and the three shells unguarded, the
    fixtures stating them: the stdin-script matrix (`tools/romp-track-bash-guard-stdin-script-matrix.json`: 6 roads x 10 shapes
    around the shell x the 5 shells of SHELLS x 2 scripts), `rows 600 refused 600 allowed 0 other 0 writes bash=480 zsh=480 dash=320
    timeouts 0`, `FALSE ALLOWS (allowed, a shell writes; the 600 rows not marked residual): 0`, `refused with no writer: absent 120`
    (ksh is not installed here); the heredoc-body matrix (`tools/romp-track-bash-guard-heredoc-body-matrix.json`: 6 delimiter
    quotings x 5 body lines x 6 consumers), `rows 180 refused 156 allowed 24 other 0 writes bash=116 zsh=116 dash=116 timeouts 0`,
    `FALSE ALLOWS (allowed, a shell writes; the 180 rows not marked residual): 0`, `refused with no writer: absent 24 escaped-paren
    16` (the 16: a quoted body's `\$(cp ..)` handed to a shell, a syntax error every shell stops on, read as a subshell running the
    copy, the parenthesis read that predates this fix-up). The verdicts of the earlier fixtures are unchanged at this commit:
    `existing rows: 1020 unchanged, 0 changed, 0 missing` (the param-word matrix), `existing rows: 300 unchanged, 0 changed, 0
    missing` (the piped-script matrix), `existing rows: 2280 unchanged, 0 changed, 0 missing` (the construct matrix). THE RESIDUALS, named here and on the hook
    header beside the earlier ones: a script a `${...}` word stands for when the guard cannot read the word (`bash -c
    "${x:-$(cat f)}"`), one fed by a redirection on the closing brace of zsh's brace-body compound (`if [[ a ]] { bash } <<'EOF'`,
    a `}` closer the frame counts and closerStdin does not match), a producer behind a pipe the guard cannot read (the second fix-up's list, `yes '..' | head -1 | bash` and `| sed '' | bash` among them; relabelled by round 6's second commit as a producer outside THE OUTPUT MODEL, which reads a subshell or a group of echo, printf and silent commands), and a command whose name is an expansion (named
    among the writers since round 4: the verifiers' `${SHELL} -c '..'`, `$SHELL <<< '..'`, `echo '..' | ${x:-bash}`, 15 rows, while
    `env ${SHELL} -c '..'` is refused by the wrapper's unknown-option rule, an inconsistency stated, not a rule). Pinned: the rows
    test's third fix-up group (139 rows: the verifiers' spellings, the three classes found beside them, the quotings, the costs, the
    residuals, and the twins of the legacy rows whose `$(echo ..)` stand-in the fix-up resolves, each by name now, the legacy rows
    keeping their intent through a pipeline the guard does not read), the two fixtures, the lexer's reads in
    `tools/romp-track-bash-guard-shapes.test.mjs`, and the plan test (the six rules on both surfaces in the same words, the
    functions, the fixtures' populations, the residuals named here, on the header and in hooks/README.md, the surfaces' sentence).
    Mutation on scratch copies: with the unquoted body kept raw, the four tests the third fix-up's name selects (the lexer's shapes, the stdin-script matrix, the
    heredoc-body matrix, the rows) print `# pass 0 # fail 4` (`H-sub: refused`, `the heredoc-body matrix: no row a shell writes is
    allowed`); with the resolved substitution disabled, `# pass 0 # fail 4` (`H-script-expanded: refused`, `the stdin-script matrix:
    no row a shell writes is allowed`); with the default word's reading removed, `# pass 2 # fail 2` (`H-script-default-word:
    refused`); with the `=(` read removed, `# pass 2 # fail 2` (`E-brace: refused`); with the compound's piped producer not read
    through the frames, `# pass 1 # fail 3` (`C-subshell: refused`, the stdin-script matrix red); with the closer's redirection not
    fed to the compound, `# pass 1 # fail 3` (`C-heredoc-on-subshell: refused`); with a script operand naming stdin read as a
    file, `# pass 1 # fail 3` (`N-dev-stdin: refused`); with the inherited stdin dropped, `# pass 1 # fail 3` (the inner-shell
    group's first row, `echo '..' | bash -c 'bash'`: `refused`; the row's label is not spelled here, since its leading letter reads
    as a first-person pronoun to the plan tests' quoted-utterance pin); with the split operand removed, `# pass 2 # fail 2`
    (`S-ifs-named: refused`); with the process-substitution script operand not read, `# pass 2 # fail 2` (`E-script-operand:
    refused`).
    ROUND 6 (2026-09-20; round 5's ruling on the third fix-up's head): THE RESOLVER'S CONTRACT. Round 5 found four readings of the
    third fix-up that turned a refusal of the base into an allow, each a text the machinery computed, believed and trusted: printf's
    width and precision ignored (`echo x > $(printf '%.9s' report.mdXX)` from docs/ judged on report.mdXX while bash, zsh and dash
    wrote report.md), an unquoted glob character switching the readings off (`bash -c "${x:-cp ../base/*.md report.md}"` handed to
    the shell unread), the octal escape without a leading zero missing from the union (`$(echo 'repor\164.md')` judged on the
    spelling while dash wrote report.md; `$(printf '%b' ..)` while bash and dash did), and THE SPLIT OPERAND exempting every
    double-quoted word (`cp "$@"` copying in every shell). The contract, stated at the reading functions in the hook and consumed in
    two places (lex's `placeReading`, extract's `scriptTexts`): a reading function answers sound texts (every text some shell could
    produce), UNRESOLVABLE (the resolver looked and cannot establish the text), or null (the resolver does not apply), and nothing
    else; a reading takes the text road, the word's literal characters judged as a target, only when plain, one text from no
    interpretation, so nothing a reader could get wrong reaches a target judgement; every other reading travels the script road,
    where a reading the union lacks can at worst leave a script as unread as the base left it; and UNRESOLVABLE refuses in both
    places, never the residual pass. printf's `%s` and `%b` are read with the `-` flag, a width and a precision, `%%` and each shell's
    escapes; every other conversion, flag, a `*` from a non-digit operand, a non-ASCII operand under a width or precision, an option
    word and a missing format are UNRESOLVABLE, and `-v` is the empty text every shell prints. Nine escape readers (echo, a printf format and `%b`, in bash, zsh and dash) are
    derived from the manuals and pinned by execution. A glob character, a brace list, a shell-dependent quoting or an expansion the
    resolver does not read in an echo operand or the default word is UNRESOLVABLE, so `s='cp ..'; echo "$s" | bash`, the piped-script
    matrix's residual-value producer, is refused now and its five rows moved out of the residual set (ids `value-unread/..`,
    verdict r, the same writers). `dqSingleField` exempts a double-quoted operand from the split rule only when proven one field
    (the `@` forms, `[@]`, `${!..}` and zsh's `(`, `=`, `~` and `^` openers may split). The crash round 5's correctness-3 found (`printf`
    with no format, `printf --`, `printf -v`: an empty reading, a TypeError, a refusal inside a project and an allow outside one
    while every shell wrote) is closed by the same rule (the missing format UNRESOLVABLE, `-v` the empty text, so
    `$(printf -v x a)report.md` is judged by name from any cwd), and the catch-all refuses from every cwd, because the walk throws before
    the hook knows what a command reaches and the cwd bounds nothing (a `cd <project>/docs && cp .. $(printf)report.md` from a
    scratch directory wrote the tracked file). Pinned: a structural test deriving the reading functions from the hook's source
    (called outside the two places, or a word's readings read elsewhere, reds), the readers and the printf forms by execution in the
    three shells, the rows test's round-6 group, the shapes test's single-field rows and the catch-all's three stages from a cwd in
    no project. Stated, not closed: zsh's glob grouping (`cp ../base/(r)eport.md report.md` handed to zsh, literal or through a
    reading) is read as a subshell by the lexer's zsh grammar and allowed while zsh copies, a lexer gap outside the resolver.
    ROUND 6, SECOND COMMIT (2026-09-21; round 5's rulings C, D, E, F and G). THE ALIAS ROAD (extra7-2): a writer behind a shell
    alias the command defines was read as an unknown command and allowed while its text stood in the command; measured by the
    shells' grammars (bash: the first unquoted word of a simple command, under `expand_aliases` when not interactive, never on the
    line that defines it, a trailing blank chaining; dash: wherever a reserved word may occur, in the input stream, so through
    `-c` on the next line; zsh: command position, `-g` in every position, `-s` a suffix, from a file or a pipe and never through
    `zsh -c`), dash copied through `-c`, zsh and dash through a here-document or a pipe, bash under the option. THE HEAD SPLICE
    reads a command name that stands for a text the shell runs in its place, the text spliced in and the segment re-lexed with its
    tail as spelled: an alias body bound on an earlier line (`aliases`; a `-g` alias makes every later unquoted word spelled so a
    target the hook cannot read; `unalias` is not read, the safe side), a hashed path (`hash -p PATH NAME`, `hash NAME=PATH`), a
    path the command made by copying or linking another command (`bound`: `cp /usr/bin/cp ../scratch/c2; ../scratch/c2 a b`), and
    the readings of an expansion the resolver established (`${x:-cp} a b` ran the copy in every shell while the reading `cp` went
    unused in head position: the contract's head role yields the readings now); a binding the resolver cannot read makes the name
    a target the hook cannot read, and an alias whose NAME it cannot read makes every later command name one. `eval` and `trap`
    with text the resolver reads are scripts of this shell (`eval 'cp a b'`, `trap 'cp a b' EXIT` ran the copy while allowed);
    `source` and `.` of the standard input read what the command reads. THE OUTPUT MODEL (tests-1): a subshell or a `{ }` group
    before a pipe, and the list inside a `$(...)`, a backtick or a `<(...)`, prints what its echo, printf and silent commands
    print (listOutput; a `cat` fed one here-document prints its body), the text placed on the closer that carries the pipe and
    read as the consumer's script; a command the model does not read beside a printer makes the list UNRESOLVABLE, refused, its
    commands still read; a list with no printer is outside the model, the residual relabelled honestly on every surface (a
    producer outside the output model: a function call, a tee, a further pipe, a cat of a file), and the piped-script matrix's
    residual set is keyed on the model, not on a hand list. THE RESIDUAL PROPERTY (C, extra7-3), below, replaces the closing hand
    list: the classes it states are those THE RESIDUAL TABLE measures, and the reviewer's narrower sentence (the hook cannot read
    a command whose text it cannot statically resolve) is withdrawn with the alias road, since the property must cover a command
    the hook can read and still does not resolve to a writer. THE EVIDENCE A ROW NEEDS (E, regression-3): the matrices' NOT RUN
    skip is keyed on the fixture's `needs`, the programs a row's evidence needs, derived by hiding each named program behind a
    scratch PATH, so a row the running shell writes before the named consumer is reached is measured on a runner without that
    consumer; a runner lacking zsh is reproduced in the test file itself. The construct matrix pins the key set of CONSTRUCT_HEADS
    by kind (F), derives its population sentence from its tables (G), and the four constructs the param-word note named without a
    row have rows.
    ROUND 6, THIRD COMMIT (2026-09-21; the round's three verifiers on the second commit's head, every finding a command a shell
    wrote onto the tracked file while the guard allowed it, each closed by refusing and none relabelled). ZSH'S UNBRACED FLAGS:
    `$=name`, `$^name` and `$~name` are zsh's `${=name}`, `${^name}` and `${~name}` without the braces (zshexpn), and the lexer
    read a `$` before `=`, `^` or `~` as a literal dollar, so `cp "$=X"` with two paths in X was a one-operand cp the split rule
    never saw, and `cp ../base/report.md $~X` a copy onto the literal name `$~X`, both allowed while zsh split, or substituted,
    and copied; expansionAt reads the three as expansions under zsh's grammar (a script handed to bash or dash keeps the literal
    dollar) and dqSingleField proves none of them one field. THE SPLIT TARGET: the resolved substitution's rule called a
    redirection target a place no shell splits, and bash and zsh split it (zsh opens every blank-separated field under MULTIOS,
    bash the one field or none of several, an ambiguous redirect) while dash opens the whole text, so `echo x > $(echo
    'report.md ')` was judged on the untracked name `report.md ` and allowed while bash and zsh wrote report.md, and `> $(echo x
    report.md)` while zsh wrote x and report.md; endWord records each field the resolver's blanks cut as a redirection of its
    own beside the whole text (expandedFields), and the rule's sentence on decision 47 says so. THE ALIAS ROAD INTO A TEXT
    PARSED LATER: a text the shell parses after the segment handing it over has run (eval's and trap's operands, a sourced
    standard input, a `$(...)`, a backtick, a `<(...)`) was lexed as its own text, its line count starting at 1, so an alias
    bound on line 1 never stood on an earlier line and `alias c=cp; eval 'c ../base/report.md report.md'` copied in zsh and dash
    (bash under `expand_aliases`) while allowed, as did `trap`, `. /dev/stdin`, `echo $(c ..)` and a backtick; lineOf gives such
    a text coordinates strictly between the outer segment's line and the next (`lineBase`, `lineStep`; recurse), so a binding on
    or before the outer line is seen inside it, a binding made inside it is seen on its later lines and on every later outer
    line, and never on the outer line itself, as the shells parse (`eval 'alias c=cp'; c a b` expands in none of them). A
    SOURCED PROCESS SUBSTITUTION and A DESCRIPTOR AS THE SCRIPT: `. <(echo 'cp a b')` and `source <(..)` (bash and zsh; zsh's `.
    =(..)` too) are read as `bash <(..)` is; a script operand naming a numbered descriptor (`/dev/fd/N`, `/proc/self/fd/N`:
    `bash /dev/fd/3 3<<'EOF'` ran the body in every shell, `bash /dev/fd/9 9<<< '..'` and `. /dev/fd/3 3<<< '..'` in bash and
    zsh) reads every body the command carries (isStdinName; the lexer keeps no descriptor on a body, so the over-read is the
    safe side); and a `--rcfile` or `--init-file` process substitution is read whether or not `-i` is spelled (bash reads it
    only when interactive: the refusal without `-i` is a stated cost). THE SED SCRIPT: sed's `w` and `W` commands and the `w`
    flag of `s` write the file they name, and sed was a writer through `-i` alone, so `sed -n 'w report.md' ../base/report.md`
    and `sed 's/x/y/w report.md' ..` wrote in every shell while allowed; sedWriteFiles reads a literal script over GNU sed's
    command grammar and sedScriptWrites judges each file by name (a plain-string name in the script resolves first:
    `f=report.md; sed -n "w $f"` refuses by name), a script whose reader stops at a letter the grammar lacks refuses naming the
    letter (sed itself rejects such a script; a reader that misread an address would stop the same way, so it does not guess),
    and a script the resolver cannot read stays the residual, named in the property. A GLOB IN THE COMMAND NAME: `/usr/bin/[c]p
    a b` ran cp in every shell while the walk read an unknown command; the sorted matches stand in the name's place through THE
    HEAD SPLICE (several make the first the command and the rest its leading operands, as the shells do), a pattern the guard
    cannot expand is a name it cannot read, and one matching nothing stands as spelled. ZSH'S OTHER HEADS: `=cp a b` (zsh's
    `=cmd`, the path of cp) is spliced under zsh's grammar, `emulate sh -c TEXT` runs TEXT as a script of zsh, and `zf_mv`,
    `zf_ln`, `zf_rm` and `zf_rmdir` (zsh/files) are the coreutils commands by another name. A CAT OF THE STANDARD INPUT inside a
    `$(...)` with nothing in the list feeding it (`echo 'cp a b' | { bash -c "$(cat)"; }`, `| bash -c 'eval "$(cat)"'`: every
    shell ran the piped text) is UNRESOLVABLE under THE OUTPUT MODEL, refused where a script is built from it; a cat after a
    pipe inside the list stays the producer outside the model. THE RESIDUAL TABLE gains the members of its classes the verifier
    found (a `$(which cp)` head and the `${...}` operator heads, setarch and linux64, uniq, awk's redirect, scp, openssl, shred,
    bash's history -w, zsh's sysopen and mapfile, a sed script the resolver cannot read, a written sed -f file), the writer
    class is restated to cover a write form of a program the hook models, and the child test that reproduces a runner lacking
    zsh counts the rows' NOT RUN line, not the probe's. Stated, not decided here: deleting or moving a tracked file (`rm
    report.md`, `mv report.md other.md`) is allowed, since the guard's contract is the write that lands on a tracked file;
    whether the tracked set shrinking is a write for it to refuse is a scope question raised with the round.
    ROUND 6, FOURTH COMMIT (2026-09-21; the round's three verifiers on the third commit's head, every finding a command
    a shell wrote onto the tracked file while the guard allowed it, each closed by refusing and none relabelled, and
    each rule keyed on the shells' grammars rather than on the spelling that found it). THE DESCRIPTOR FEED: a script
    operand naming a numbered descriptor reads a `<` on that descriptor too (`bash /dev/fd/3 3< <(echo 'cp a b')`,
    `python3 /dev/fd/3 3< <(..)` and `. /dev/fd/3 3< <(..)` ran the printed text in bash and zsh while textsOf skipped
    every `<` off the standard input; shellScript answers the descriptor named, fdOfName, and stdinBodies reads it; a
    `<` on a descriptor no operand names stays unread, since the shell reads its script elsewhere). THE EXEC FEED: a
    bare `exec` with redirections alone opens them for the rest of this shell and for the processes it starts (`exec
    3<<< 'cp a b'; . /dev/fd/3` and `exec < <(echo 'cp a b'); bash` ran the text in bash and zsh), so its bodies feed
    every later consumer (execFeeds, shared by every recursion). THE ALIAS BODY: a body holding a `$` or a backtick
    after quote removal is expanded when the alias is USED (`alias c='$x'`, then `x=cp`, then `c a b` copied in dash,
    and through a here-document in every shell), so it binds null, refused as a text the resolver does not read, as an
    expansion at the definition already did; a `-g` alias at a redirection target is refused as one among the words is
    (`alias -g R=report.md` then `echo x > R` wrote in zsh); zsh's `functions[NAME]=BODY` binds NAME as an alias does.
    THE BOUND PATH: a path the command made by copying or linking a command is looked up by the head's text however
    spelled (`'../scratch/c2'`, `"$PWD/../scratch/c2"`, `$x` resolved to it: the lookup read the unquoted literal
    spelling alone), by a pattern's matches among the paths bound (`../scratch/c?`: the file is made when the command
    runs, so the filesystem cannot expand the pattern at check time), through PATH for a bare name (`ln -s /usr/bin/cp
    ../scratch/c2; PATH=../scratch c2 a b`), and a `cat FILE > DEST` binds DEST as cp does; a head through a HOME the
    command reassigns, or through a PATH set to a value the resolver does not read, is one the hook cannot read while a
    path is bound. THE COMPOUND PRODUCER: a keyword compound before the pipe (`for i in 1; do echo 'cp a b'; done |
    bash`; while, until, if and case alike) prints what the list from its head to its closer prints, and the head runs
    the body a number of times the model does not count, so a printer inside it makes the list UNRESOLVABLE (placed on
    the closer segment that carries the pipe, listOutput naming the head) and a body with no printer stays outside the
    model; dash reads `(( list ))` in command position as a subshell in a subshell, so `((echo 'cp a b')) | bash` prints
    the list's text there (bash and zsh read arithmetic and stop), the reading placed as the producer's. THE OPTION
    TERMINATOR: `eval -- TEXT` (bash and zsh), `. -- FILE` and `source -- FILE` read past the `--`. THE HEAD CANDIDATES
    (extract): every plain-string value ANY assignment word of the command gives a name, in every scope and form,
    whitespace included, shared by every recursion; a word that is one `$name` expansion the readability rule did not
    resolve stands for each value where it is a command name or a script (scriptTexts, roles 'head' and 'text'), the
    script road's union, so `c=cp; export c; $c a b`, `(c=mv); c=cp; $c a b`, `c=cp; echo '$c'; $c a b`, `declare c=cp;
    $c a b`, `eval c=cp` then `$c a b`, `c=cp bash -c '$c a b'`, `env c=cp bash -c '..'`, `f() { local c=cp; $c a b; };
    f`, `c='cp a b'; $c`, `bash -c "$c"` and `eval "$c"` refuse (the last three were the residual "a script held in a
    variable", whose class is restated to the names a construct the resolver does not read fills in); a target keeps the
    readability rule, whose safe side is the refusal it already gives an unreadable name; the glued default word
    (`${c:-c}p a b` ran cp in every shell while the reading `c` was dropped for the glued `p`) carries its reading with
    the literal text around it (THE GLUED READING, readingsOf in lex). THE IFS RULE: while the command names IFS, an
    expansion not inside one pair of double quotes splits at IFS's characters, a rule the resolver does not compute, so
    the readability rule does not read it there (a target refuses as one the hook cannot read, a copying writer's one
    operand as split, a command name through scriptTexts) and lex declines to resolve a substitution at a redirection
    target too (`IFS=:; echo x > $(echo 'report.md:x')` opened report.md in zsh under MULTIOS; `x=a:report.md; IFS=:;
    tee $x`, `cp $x` and `IFS=: eval '..'` wrote in bash and dash), the rule holding in every text the command hands
    over. THE FED SUBSTITUTION: a `$(...)`, a backtick or a `<(...)` whose list the resolver does not read runs a
    command outside the output model, which may read the standard input, so where this command feeds that input with a
    text the guard read (a pipe from a producer it reads, a closer's redirection, an exec feed, the caller's) the word
    is UNRESOLVABLE (`echo 'cp a b' | bash -c "$(head -1)"`, `$(sed '')`, `$(tr a a)`, `$(awk 1)`, `$(dd)`,
    `$(</dev/stdin)`, `$(command cat)`, `$(busybox cat)` and `bash <(cat)` each ran the piped text while the rule that
    refused `$(cat)` was keyed on the spelling `cat`); with nothing fed the text is not in the command and the word
    keeps the residual; a process substitution so marked is recorded (cannotRead dropped every `<(..)` before); the
    cost, stated and pinned: a cat of a FILE in a fed segment refuses too. THE SED FILE: sed's `-f FILE` naming the
    standard input or a descriptor this command feeds stands for the bodies fed, a `<(..)` for the text it prints, each
    read over the sed grammar (`sed -n -f /dev/stdin f <<< 'w report.md'`, `-f <(echo 'w report.md')`, `-f /dev/fd/3 ..
    3<<< '..'`, `--file=<(..)` and the here-document form wrote in bash and zsh, dash through the here-document). THE
    VALUED NAMES: the value of PS0, PS1, PS2, PS3, PS4 and PROMPT_COMMAND is a script of this shell (bash runs a prompt
    string's `$(..)` when it prints the prompt or traces a command: `PS4='$(cp a b)'; set -x; :`, `PS4='..' bash -xc :`,
    `export PS4=..` and `PROMPT_COMMAND='cp a b' bash -i` ran the copy), ENV and BASH_ENV name a file the shell sources,
    read when it is a `<(..)` the resolver reads (`ENV=<(echo 'cp a b') dash -i`; the lexer keeps a glued `<(..)` in its
    word as bash does, `ENV=/dev/fd/63`), bash's `${name@P}` runs the value's `$(..)` (each candidate value read), and
    `mapfile -C CALLBACK` runs the callback (SCRIPT_VALUED_NAMES, STARTUP_FILE_NAMES, readValuedWords). ENV'S OPERAND:
    after env an assignment operand however quoted is env's (`env 'X=a b' cp a b` copied in every shell while the quoted
    word was read as the command name). THE RESIDUAL TABLE gains the members its classes lacked (unshare, setpriv, perf
    and prlimit, wrappers outside the set; parallel, a reader like xargs; an alias in a sourced written file; an eval
    printing before the pipe; perl's File::Copy) and loses the two THE HEAD CANDIDATES read.
    ROUND 6, FIFTH COMMIT (2026-09-21; the round's three verifiers on the fourth commit's head: every finding a command
    a shell wrote onto the tracked file while the guard allowed it, each closed by a rule fitted to its class, none
    relabelled, and the table gaining the members its classes lacked). THE PARAMETER'S VALUE (defaultWordReading, lex's
    defaultReading, extract's scriptTexts): a default word's text is the parameter's value when it is set and the word
    otherwise, and the reading was the word alone, so `c=cp; ${c:-cat} a b` ran the copy in every shell (and `${c-cat}`,
    `${c:-}`, `${c:-''}`, `"${c:-}"`, `${c:?}`, `${c?}`, `${c:=cat}`, through `eval "${c:-cat} a b"`, as a piped
    script's consumer and as a here-string's); the reading carries the name (`params`, with the literal text glued
    around the expansion, so the value stands where the expansion stands) and scriptTexts joins the value the
    readability rule and THE HEAD CANDIDATES hold for it, refusing the word as UNRESOLVABLE where that value is not
    readable: a name a construct the resolver does not follow wrote (`read c`, `c=$(which cp)`), one a value the
    resolver could not establish was given, or one the command never sets, whose value is the shell's own (a
    `${X:-default}` command name or script from a tracked cwd with X untouched refuses, a stated cost; the `+` forms
    depend on no value and keep the word alone; a default word glued to another expansion is UNRESOLVABLE). THE MOVED
    SHELL (extract's return, recurse's adopt): a cd inside a text this shell ran in place (eval's text, a sourced
    standard input, here-string or `<(..)`, a head splice, emulate's and mapfile's texts) moved nothing for the rest of
    the command, so `eval 'cd ../notes'; cp ../base/report.md n1.md` landed on the tracked notes/ in every shell while
    the copy was judged from docs/ (with `eval "cd $d"`, `pushd`, `. /dev/stdin`, `source /dev/stdin <<< ..`, `. <(echo
    ..)`, an alias whose body is a cd, `alias c=cd`, `c=cd; $c ..`, inside a function, and the copy through cp, mv, tee,
    a `>`, sed -i, python or `bash -c`); the sub-walk's directory state comes back and is adopted, recorded on the
    frames and on a function body around it, and a trap action that moves leaves the directory unknown (`trap 'cd
    ../notes' DEBUG; cp ..` moved bash and zsh before the cp). THE DUPLICATED DESCRIPTOR (lex's dups, fdsFor): `[n]<&m`
    was skipped, so `exec 3< <(echo 'cp a b'); bash <&3`, `bash 0<&3`, `bash 3< <(..) <&3`, `{ bash; } 3< <(..) <&3`,
    `bash /dev/fd/4 4<&3` and `exec <&3; bash` ran the text in bash and zsh; a consumer reads every descriptor a dup on
    its segment or on an exec feed reaches, to a fixpoint, and a dup from a word the lexer cannot read reads every
    descriptor fed. THE PASSED-THROUGH TEXT (passthroughCat, pipedScripts): a plain `cat` of its standard input before a
    pipe prints what feeds it (`echo 'cp a b' | cat | bash`, `cat < <(echo ..) | bash`, `exec 3< <(..); cat <&3 | bash`,
    `(echo ..) | cat | bash` and `| (cat | bash)` each ran the text in the shells named), so that text is the consumer's
    script; a cat with an option word is UNRESOLVABLE where a text is fed (`cat -s` passes a script unchanged), a cat of
    a file stays the residual, and the property's fifth class says so. THE STARTUP FEED (the shells' branch): a BASH_ENV
    or ENV value naming the standard input or a descriptor the shell is fed is the text fed, sourced at startup
    (`BASH_ENV=/dev/stdin bash -c : <<< 'cp a b'`, `echo '..' | BASH_ENV=/dev/stdin bash -c :`, `BASH_ENV=/dev/fd/3 ..
    3< <(..)`, through export, env and a nested `bash -c`, and `ENV=/dev/stdin dash -i -c :`), read whether or not this
    shell would. THE EXPORTED FUNCTION (the walk; commandOf's env operand): env sets any operand holding a `=`, and a
    bash the command starts imports `BASH_FUNC_NAME%%=() { .. }` as the function NAME, so the quoted word was read as a
    command name while `env 'BASH_FUNC_c%%=() { cp "$@"; }' bash -c 'c a b'` (and through `env -i`, `echo c | env ..
    bash`, `bash -s <<< c`, a `BASH_FUNC_cat%%` shadowing cat) copied in every shell; the word is a definition, its body
    read as `export -f`'s is. THE SPLICED DEFINITION (defLineOf): a definition made inside a head splice bound at
    Infinity, after every later use, so `alias a=alias`, then `a c=cp`, then `c a b` copied in dash (and, through a
    here-document or a pipe, in every shell); it binds at the spliced segment's line. THE CALLED BODY (functionBodies,
    popFunction, the walk, recurse's runFunction and callArgs): a function the command defines, called where a text the
    guard holds feeds it, was an unknown command while its body ran a shell on that text (`f() { bash; }; echo 'cp a b'
    | f`, `f <<< ..`, `f <<'EOF'`, `f < <(..)`, bodies of `sh`, `cat | bash`, `. /dev/stdin` and `bash "$@"` called with
    /dev/stdin, the call inside a subshell or a group); the definition's text is kept by name and replayed at the call
    with the fed text on its standard input and the call's operands, a call inside its own body not followed again. THE
    HEAD CANDIDATES' three gaps (noteCandidate, candidateTexts, scriptTexts): `+=` appends (`c=c; c+=p; $c a b` copied
    in bash and zsh), a value's newline is a blank where the value is a command name (`c='cp<newline>a b'; $c` copied in
    bash and dash), and two names in one quoted text compose (`a=cp; b='a b'; eval "$a $b"`, `bash -c "$a $b"` and `sh
    -c "$a $b"` copied in every shell); and THE ASSIGNMENT VALUE (lex's assignmentValue, noteCandidate's value road): no
    shell splits an expansion's result in an assignment's value, while the lexer cut `x=$(echo 'cp a b')` into three
    words and the candidates read `cp` alone (`$x` then copied in bash and dash), so the value is one text, and a value
    that is a reading on the script road (`x=$(printf '%s' 'cp a b')`) is a candidate through scriptTexts, one the
    resolver could not establish marking the name (unreadValues), refused where the name is a command name or a script.
    THE RESIDUAL TABLE gains the members its classes lacked that the verifiers measured: zsh's `${=c}`, `${~c}`,
    `${(z)c}`, `$=c`, `${(L)c}`, `${c:s/x/p/}` and `${c:q}`; bash's `${c:0:2}`, `${c:0}`, `${c,}`, `${c@P}`, `${c@E}`,
    `${c//x}`, `${c#}` and `${c%?}`; arrays by every spelling; getopts's OPTARG, REPLY, select and a loop variable after
    its loop; a function's positionals and its `eval "$*"`; `${d:=$c}`, `declare d=$c` and `set -- $c`; a `read` or
    `mapfile` of a fed text, inside a called body too; the loader `/lib64/ld-linux-x86-64.so.2`; xargs by every
    spelling; a written `.zshenv` read through ZDOTDIR or HOME; a name glued to another expansion in head position; an
    eval, a backgrounded echo, `time`, `yes | head`, a second `| bash` and a tee before the pipe; python's `os.truncate`
    and `os.write`, and its `os.system` through a called body or a descriptor. The contract paragraph says on its four
    surfaces that deleting or moving a tracked file away is not a write the guard refuses, a scope question raised with
    the round's review. Stated costs, each pinned with no shell writing: an untouched `${X:-word}` command name or
    script from a tracked cwd; `cat -n` before a pipe fed a text; `exec 3<<< ..; BASH_ENV=/dev/fd/3 bash -c :` (bash
    does not read it there); `env 'BASH_FUNC_..' sh -c c` (dash imports nothing); a function calling itself before its
    shell.
    ROUND 6, SIXTH COMMIT (2026-09-21; the round's three verifiers on the fifth commit's head, an attack lens, a
    residuals lens and the body auditor: every finding a command a shell wrote onto the tracked file while the guard
    allowed it, three of them roads by which a text the hook could not establish reached an allow through a null; the
    mechanism is fixed once, stated here, and the rows follow from it). THE APPLIED RESOLVER (printerOf,
    shapeOnPrinter, segmentOutput, listOutput, closerOutput): once the resolver applies to a segment (its head is a
    literal echo or printf, or a cat fed a here-document, alone or in a list or group of them), every shape it does
    not model is UNRESOLVABLE, never null: a redirection, a here-document, a `<`, a substitution or an arithmetic body
    on the printer (`echo 'cp a b' 2>/dev/null | bash`, `</dev/null`, `3>/dev/null`, `>/dev/stdout`, `2>>`, `2>|`,
    `2<>`, zsh's MULTIOS write forms, the same inside `$(..)`, a here-string, a `<(..)` and a here-document, each ran
    the text in the shells named while the printer was dropped as outside the model and the list read as
    printer-less), a `&&`, `||`, `&` or `|` after it inside a list (`(echo 'cp a b' && true) | bash` and its `||`, `&
    wait` and `| cat` forms ran the text in every shell), and a redirection on the closer of the subshell or group
    holding it (`(echo ..) 2>/dev/null | bash`, `(time echo ..) 2>/dev/null | bash`); null is reserved for a segment
    whose head is no printer at all, the residual the property names; pinned by execution over every list operator and
    every redirection operator the lexer has. THE UNREAD SCRIPT WORD (scriptTexts): a script word that is no expansion
    and still not literal (a glob character, a brace list past the cap, a quoting whose reading depends on the shell)
    is a text the resolver cannot establish, refused (`bash -c cp\ ../base/*.md\ report.md`, `[r]eport.md`,
    `?eport.md`, the same through `sh -c`, `dash -c` and `eval`, python's and node's inline words holding a `*`, each
    ran in bash and dash while no text was read and nothing was refused). THE SPECIAL PARAMETER (lex's braceParameter,
    defaultWordReading): a default word over a digit run or a special parameter is a default word too; the `+` forms
    stand for the word alone, a `-`, `=` or `?` form over `#`, `?`, `0`, `$`, `!`, `-`, `@` or `*` stands for a value
    that is the shell's own, UNRESOLVABLE, and one over a positional parameter carries the name to THE POSITIONAL
    VALUE (`${#:+cp} a b`, `${0:+cp}`, `${$:+bash} -c '..'`, `${1:-cp} a b`, `${@:-cp}`, `${!:-cp}`, `${0:-x} -c '..'`
    ran the copy in the shells named while the grammar read names alone). THE ASSIGNED DEFAULT (lex's paramAssigns,
    extract's noteCandidates): `${name:=word}` and `${name=word}` give name word's texts as candidates, a word the
    resolver cannot establish marking the name (`: ${e:=cp}; $e a b`, `true ${e:=cp}`, `x=${e:=cp}`, `: ${e:=cd}; $e
    ../notes; cp ..`, `: ${e:='cp a b'}; eval "$e"` ran in every shell while the assignment was recorded nowhere). THE
    SHELL'S OPTION WORD (shellScript's optionWord, the walk's readShell): a word in option position of a shell in
    SHELLS, with words after it, that the resolver did not read stands for each text it can (its readings, a
    candidate, a positional), the shell read again with each in its place, and for none is refused on the side
    WRAPPER_OPT takes for an option a wrapper's table does not know, every later word a target the hook cannot read;
    as the last word it is the operand, so `bash -c "$x"` keeps the residual (`set -- -c; bash "$1" 'cp a b'`, `bash
    "${f:--c}" ..`, `f=-c; bash ${f-x} ..`, `a=(-c); bash "${a[@]}" ..`, `bash {-c,} ..` ran the script in the shells
    named while the expansion was taken as the script FILE operand and the `-c` it stood for was never seen). THE
    POSITIONAL VALUE (bindPositionals, positionalWords, expandPositionals, setOperands, positionalsApply, the walk;
    CANDIDATE_TOKEN and RESOLVED_NAME take a digit, `$@` and `$*`): THE CALLED BODY's replay runs for every call, fed
    or not (`f() { bash "$@"; }; f -c 'cp a b'`, `f() { bash -c "$1"; }`, `"$*"`, `eval "$1"`, `"$@"` and `$1` as the
    command name, a nested call, `f() { bash <<< "$1"; }`, `eval "cp $1 $2"` ran in every shell while the replay ran
    for a fed call alone), and the positional parameters this shell holds are the replayed call's operands or those a
    `set` with no option word gave (`set -- 'cp a b'; eval "$1"`, `set -- cp a b; "$@"`, `$*`, `set -- x cp; shift;
    "$@" ..`), standing in place of a whole word that is one of them, read through the readability rule and THE HEAD
    CANDIDATES for a `$N` inside a word, and joined by one blank for `"$*"` and `"$@"` in a here-string or an unquoted
    here-document body; a `shift` by a count not read, a `set` whose operands or option words the resolver does not
    read (`set -A` is zsh's array assignment), an `eval` of a text it does not read or a sourced file rebinds them to
    values not known, after which a positional word is UNRESOLVABLE; a body being defined has positionals of its own
    (`set -- cp; f() { $1 a b; }; f cat` runs cat, allowed), the replay reads a body's aliases as of the definition's
    line (functionLines: `f() { c a b; }`, then `alias c=cp`, then `f` expands in no shell), and a fresh or fed
    shell's positional parameters are its own, not read (`bash -c '$1 a b' _ cp`, the residual). THE EMPTY ALTERNATIVE
    (lex's braceEmpty, the walk's variants): bash drops an unquoted empty word a brace list expands to and zsh keeps
    it, so a writer's operands are judged under both readings and an empty word in command position is dropped (`{cp,}
    a b`, `{mv,} a b`, `{bash,} -c '..'`, `{,cp} a b` copied in bash while the lexer's empty operand was judged as `cp
    '' a b`, a copy no shell performs). THE RESIDUAL TABLE loses the fifteen rows these rules refuse (the positional
    rows, the function-body rows, the inner pipe, the backgrounded and the timed echo, `${d:=$c}`) and gains the
    members the verifiers measured that no rule reads: a function's call of itself, zsh's autoload of a written file,
    a `.` reached through a value, nsenter, tmux, an alias in a sourced written file, a fresh shell's own positional
    parameters, a `read` value as a trap action or inside a `-c` script; the property's second, third and fourth
    classes are restated for them. Stated costs, each pinned with no shell writing: `echo "$(cat f)" | bash` (a
    substitution in a printer's operand), `bash -c "$x" _ a b` (an expansion before further words), `${#-cp} a b` (a
    `-` form over a special parameter); `bash -c "$x"` alone stays the residual and `bash -c "${x:-..}"` the fifth
    commit's stated cost: two spellings, two rules, each stated.
    ROUND 6, SEVENTH COMMIT (2026-09-21; the round's three verifiers on the sixth commit's head, an attack lens, a
    residuals lens and the body auditor). A regression, an unsound reading and the round's pre-existing allows, the
    mechanism fixed and the rest disclosed as rows. THE SPLICED PRINTER (printerOf, splicedPrinter, splicedOutput):
    the sixth commit read printerOf on the raw words, so a command name that is an expansion was a head no printer,
    a null the caller read as no printer, and `e=echo; $e 'cp a b' | bash` was allowed while every shell ran the
    printed text, where the round-5 head had refused it by name; the head candidate is resolved and the segment
    read again with each text spliced BEFORE printer-ness is decided (the order the writer, consumer and passthrough
    heads already had), so a resolved echo or printf head is the printer and its printed text is read, a text no
    candidate makes a printer staying null. THE UNSOUND UNICODE (shellEscapes): zsh renders a bare `\u` or `\U` (no
    hex digit) as a NUL that command substitution drops, so the script the shell ran was the text before it while the
    reader modelled the two characters; every `\u` and `\U`, bare or with hex, is now Undecodable for every reader.
    THE SHADOWED BUILTIN and THE DEFINITION'S NAME: a function the command defines under a builtin's name (cd, pushd,
    popd, chdir) runs through THE CALLED BODY, not the builtin, and the name of a `name()` definition moves nothing.
    THE PARAMETER TABLES: zsh's `aliases`, `galiases` and `saliases` bind an alias as `alias`, `alias -g` and
    `alias -s` do and `commands` a hashed path as `hash` does, keyed and whole-array forms. THE COMPOSED VALUE: a
    value whose expansions are names the command gives values (`c=$1`, `c="$*"`, `c=$d`) stands for their
    composition, so a positional laundered through a name and split by the shell is read, a top-level `set` seeded
    into the candidates. THE POSITIONAL LIST'S SPELLINGS: `${@:N}`, `${@:N:M}`, zsh's `$argv` and `${@[N,M]}` read
    as the list. THE EMPTY ALTERNATIVE among a call's operands is judged under bash's reading and zsh's. The head
    splice reconstructs its siblings from a resolved word's text, not its raw spelling, so a `"$@"` already expanded
    is not re-expanded. Every remaining allow-and-write the verifiers measured is a residual table row with its
    writers: the positional operator forms, a file the command writes then runs through a substitution or a
    process substitution, a decode, an inner shell's output, fakeroot and rbash, a producer outside the output
    model (a `bash -c cat` in a pipe, zsh's `print`, a NULLCMD here-string, a cat of a process substitution), and
    python's os.rename, os.replace, an exec'd write and an aliased open.
    ROUND 6, EIGHTH COMMIT (2026-09-22; the round's three verifiers on the seventh commit's head, an attack lens, a
    residuals lens and the body auditor). The regression closed through every wrapper, two mechanism defects that let
    a shell write while the guard allowed, and the rest disclosed as rows. THE WRAPPED PRINTER (commandOf, printerOf):
    the seventh commit's splice restored the bare `$e 'cp a b' | bash` refusal and left the same printer behind a
    wrapper allowed (`e=echo; command $e 'cp a b' | bash`, and env, nice, exec, builtin, time, nohup, timeout,
    stdbuf, setsid, ionice, taskset, chrt, flock, numactl, sudo and zsh's modifiers, piped and substituted), where the
    round-5 head had refused each as a wrapper option it did not read; commandOf records the word its walk stopped at
    (`at`), and printerOf splices an expansion standing there through THE SPLICED PRINTER, the segment re-lexed and the
    wrapper peeled again on the spliced text: one road for the printer, as the writer, consumer and passthrough heads
    have. THE VANISHING OPERAND (mayVanish, vanishVariants, the copying writers' case, recordMutations): a copying
    writer with three or more operands, one an unquoted expansion the shell may make no word of (an unset or empty
    name, `${c:-}`, an empty substitution, `$*`, `$@` and `"$@"` with no positional parameter, an empty array, a
    pattern under nullglob or null_glob with the directory unknown), was read as a copy into a directory named by the
    tracked file and allowed while every shell ran the two-operand copy onto it; by the resolver's contract an operand
    whose presence the guard cannot establish makes the operand COUNT a set, so the destination is judged under the
    list as spelled and under every list with such operands dropped, a write under any of them refused naming the
    operand dropped, the bound paths and class H recorded under each list, a rename or a hard link with such an
    operand marking every literal operand as a path the command may have changed, and more than VANISH_CAP such
    operands a target the hook cannot read; the never-empty forms (an arithmetic expansion, a `${#name}` length,
    `$?`, `$$`, `$#`, `$0`, a double-quoted word the guard proves one field, a literal character beside the
    expansion) stay one operand. THE PAREN RULE (parenCloses; the lexer's scope markers, skipNested, closeSubshell):
    an unparenthesised case pattern's `)` inside `( .. )` or `$( .. )` closed the lexer's subshell or substitution, so
    the producer after it was lost and `(case x in x) echo 'cp a b';; esac) | bash`, `bash -c "$(case ..)"`, the
    here-string, the here-document and the process substitution were allowed while every shell ran the text, where
    the walk's closeSubshell already knew that in a case body a `)` ends a pattern; the rule has one home now, asked
    by the walk over its frames and by the lexer over the scopes it tracks (a `(` marker, a segment headed by `case`,
    its `esac`), so such a `)` is a marker that pairs with no `(` and a substitution reads past it, and the case beside
    its printer is UNRESOLVABLE (THE COMPOUND PRODUCER). The residual table gains the names the shell itself sets
    (`$0`, `${0}`, `"$0"`, `$BASH`, `$SHELL` and `$ZSH_ARGZERO` as the command, with `-c`, a here-document and a pipe,
    and `$_` after a command), zsh's hook functions (`chpwd` and `chpwd_functions`, whose body runs where the cd lands
    while the definition is judged where it stands) and zsh's `(N)` glob qualifier; the property's third class names
    the shell-set names and an eighth class the hook functions. The piped-script matrix names, in a field of its own,
    the allowed rows whose writer evidence needs ksh, a shell no box running the matrix has, so their allow rests on
    ksh's `[[` grammar (TEST_ARITH_SHELLS) and on no measured writer.
    ROUND 6, NINTH COMMIT (2026-09-22; the round's three verifiers on the eighth commit's head, an attack lens,
    a residuals lens and the body auditor). Four defects of the round's own class, a reading that resolves a
    word wrongly and thereby allows, each fixed at the mechanism, and the rest disclosed as rows. THE POSITIONAL
    TARGET (positionalWords' target mode, expandPositionals): a redirection whose target is a positional list of
    several elements was joined into one quoted name, so `set -- a.md report.md; echo x > $@` wrote report.md in
    zsh, which opens every element under MULTIOS, while the guard judged the name `a.md report.md` and allowed;
    `"$@"` kept the first element alone; a single unquoted element's pattern went unexpanded while bash expands
    it at a target. The list stands now for the joined name dash opens (measured from notes/: the file `a.md
    n1.md`) beside each element zsh opens, a single unquoted element for itself with its pattern read, an
    element that is an expansion for a target the hook cannot read, one redirection per word, under every write
    operator, on a closer's and an `exec`'s redirection. THE PEELED NAME (commandOf's wrapperIdx; nameRoads,
    boundRoad): the alias, hash and bound-path roads were asked of the head the wrapper walk left, so a binding
    of a wrapper's own name was never seen once operands followed it: `alias command=cp`, then `command a b`,
    copied in dash, and every name of the wrapper set, zsh's modifiers, `[` and `[[`, through a here-document or
    a pipe in every shell; `hash -p /usr/bin/cp env` then `env a b` in bash, `hash env=/usr/bin/cp` in zsh; a
    copy or link of cp at `../scratch/env` on PATH, as `env a b`, as `../scratch/env a b` and behind `nice`, in
    every shell. Every word the walk peeled is asked the three roads, the binding spliced at that word with the
    words around it as spelled and the wrapper peeled again on the spliced text, an unreadable binding refused
    as the head's is; `[` and `[[` take the alias and hash roads by their text, and an alias whose name the
    lexer marks a pattern keeps its plain body. THE VANISHED TEXT (candidateTexts' vanish, scriptTexts,
    noteCandidate): an expansion the command never gives a value may be empty, and the shell drops the empty
    text before a script is handed over, so `eval cp $c a b`, `eval cp "$c" a b` (eval joins its operands and
    parses the join), `eval cp $(true) a b`, `eval cp "$@" a b`, mv, install and `ln -f` the same, `trap "cp $c
    a b" EXIT`, `bash -c "cp $c a b"` through sh, dash and zsh, behind nice and command, in a subshell, a group,
    an if and after `&&`, `flock -c`, zsh's `emulate -c`, python's inline code, and `x="cp $c a b"` run as `$x`,
    `eval $x`, `sh -c "$x"`, `bash <<< "$x"`, through declare and export, each ran the two-operand copy in every
    shell while allowed (the single-quoted spellings, the default words and a value the command gives c were
    refused). The text with every such expansion removed is one script the shell may run, read beside the
    residual (the word stays opaque, its other values not read), and never in THE SHELL'S OPTION WORD's place,
    where an empty answer is the refusal (`a=(-c); bash "${a[@]}" 'cp a b'` would read as a script file and
    pass). THE WRITTEN PROCESS SUBSTITUTION (lex's streamSite and procsubFeeds, streamOutput, outDups and the
    descriptor of a write; extract's recurseSubs and inheritedTexts): a write redirection whose target is
    `>(cmd)` is a pipe into cmd, so what the command prints (or a subshell's or group's list before the
    redirection) is cmd's standard input where the redirection is on the standard output or on a descriptor a
    `>&` of the command routes it to, UNRESOLVABLE where an `exec` opens it for every later command, and outside
    the model on another descriptor or from a command that is no printer (a cat of a file, the residual); zsh's
    `>>(cmd)` reads as `>` and the substitution. `echo 'cp a b' > >(bash)` and thirty-nine forms (printf, `1>`,
    `>|`, `>>`, `&>`, sh, zsh, dash, env bash, command bash, `bash -s`, `cat | bash`, a subshell, a group, exec,
    `3> >(bash) >&3`, a resolved `$e` printer bare and behind command, a redirection and a `sed -i` in the text)
    ran in bash and zsh while allowed, where the same `>(bash)` fed by a tee or a cat was read. The residual
    table gains sed's `s///e` flag and bare `e`, logsave, script's typescript, node's writeFileSync under
    another name, python's Path held in a name, dbus-run-session and capsh, and through `>(..)` a cat of a file,
    a `while read` and a python; the property's fifth class names the write redirection into a process
    substitution. The eighth commit's records on the hook header, this decision, the piped-script fixture and
    the tests date it 2026-09-22, the day of its commit. Every fix is pinned by execution in the ninth commit's
    rows test, the writers measured in bash, zsh and dash, red on the eighth commit's head.
    ROUND 6, TENTH COMMIT (2026-09-22; the round's three verifiers on the ninth commit's head): eight defects of the
    round's own class (a reading that resolves a word wrongly and thereby allows), each fixed at the mechanism. THE IFS
    RULE over a positional list (positionalWords): `"$*"` joins the parameters by the first character of IFS, and dash
    joins `"$@"` at a redirection target, so a named IFS the resolver does not read leaves the joined name unknown (`set
    -- .. docs report.md; IFS=/; echo x > "$*"` wrote ../docs/report.md in every shell while allowed). THE MULTI-DIGIT
    POSITIONAL (resolveWord, positionalSpelling): an unbraced `$10` is `${1}0` in bash and dash and the tenth positional
    in zsh, so the word is left unread where zsh may run the line; `${10}` is the tenth in every shell. THE ALTERNATE
    VALUE (defaultWordReading, scriptTexts): `${name:+word}` stands for the word when the name is set and for nothing
    otherwise, so the dropped form joins the readings where the name may be unset (`eval cp ${c:+x} a b` ran the
    two-operand copy while the three-operand reading allowed). THE VANISHED TEXT on a prompt road (readValuedWords): a
    prompt name's value is read through scriptTexts, the expansions the command never values removed. THE VANISHING HEAD
    (the head splice): a command name that is an expansion the command never values may be empty, so the next word is the
    command and the segment is read again with the head dropped (`$c cp a b` copied in every shell while `$c` was the
    command name). THE ROUTED STANDARD OUTPUT (lex's onStdout): the standard output reaches a process substitution along a
    chain of `>&` dups and out of a subshell's, group's or compound's body. THE PEELED NAME's two roads: `[[` is searched
    through PATH, since dash runs a bound one, and an unquoted glob-shaped name after `function` is the function's name.
    The residual table: RT-glued-plus-head is refused now and RT-run-written-prefix added (199 rows). Every fix pinned by
    execution in the tenth commit's rows test (49 rows, the writers measured in bash, zsh and dash), red on the ninth
    commit's head.
    ROUND 6, ELEVENTH COMMIT (2026-09-22; the round's two verifiers on the tenth commit's head): a regression of the
    round's own class, a fix not fitted to its class, a crash in the tenth's code, and the tenth commit's deferred list
    closed, fixed or filed. THE COUNTED SLICE (positionalSpelling, positionalWords): an offset `$#` in a positional slice
    was read as a slice from past the end, so nothing was picked and `set -- other.md report.md; echo x > ${@:$#}` allowed
    while bash and zsh wrote, where the round-5 head refused; `$#`, `${#}`, `${#@}` and `${#*}` as an offset or a length
    are the count of the parameters, resolved against the list where the walk holds it (the offset that is the count is
    the last element; with no parameter, the slice from 0 the resolver does not compute; the length that is the count
    reaches the end), and a slice of a list the walk does not hold stays unknown. THE VANISHING HEAD's one home
    (headMayVanish, vanishedHeadTexts, activeHeadTexts, passthroughCat): the tenth commit's dropped-head reading reached
    the writer and consumer heads in the walk and not the printer, which lex reads through activeHeadTexts, nor the
    passthrough cat, so `$c echo 'cp a b' | bash` and twenty-five printer forms ran the text in every shell while allowed;
    the predicate has one home, every consumer of a head word reads it, the printer reads the head as THE VANISHED TEXT
    reads a script word (the empty text where the command never gives the name a value, so `e=echo; $e .. | bash` keeps
    its one text and its refusal by name), and a command holding an expansion is read again once its values are noted. THE
    ALTERNATE VALUE at the top level (posKnown): the positional parameters are not modelled there (null), so the count
    read threw and `eval cp ${1:+x} a b` refused through the catch-all as an error of the guard's own; the list is read
    only where it is modelled, the dropped form joins the readings and the refusal is the rule's, by name. THE BOUND NAME
    (boundRoad, recordMutations' absSpelled): under a PATH the resolver cannot read, or a directory it does not know,
    every bound path whose last component is the name is spliced, so the bound writer's operands are judged by their own
    project from any cwd (`cp /usr/bin/cp <out>/scratch/env; PATH=<out>/scratch:$PATH; env <proj>/base/report.md
    <proj>/docs/report.md` from a cwd in no project allowed while every shell copied, where the same line from the
    project's directory and the alias and hash roads from that cwd refused); and a made path is bound under its spelled
    name beside the path a link the command makes resolves to (an `ln -s` binding was keyed on its target and found by no
    name). THE KEYWORD DASH RUNS (dashCommandRoads at the function, coproc and repeat sites; the head's roads defined
    before any keyword is read): a word bash and zsh reserve and dash runs as a command name is asked the alias and
    bound-path roads before the walk consumes it, the binding spliced beside the construct's own reading (`alias
    function=cp`, then `function a b`, copied in dash while allowed, and so did coproc and repeat, where select, foreach,
    time, `[[`, `]]`, end, always and declare aliased so took the roads at the head and refused). The residual table gains
    51 rows (250 rows over the same 8 classes): the FIFO a command makes with a shell reading it in the background, the
    coprocess zsh starts and feeds, a call of a function the command defines before `>(bash)`, and the members of stated
    classes the verifiers measured writing with no row (creation under the tracked notes/ folder by touch, mktemp, split
    and csplit; ruby -i; mawk's and nawk's system; unzip -o, cpio -p, xxd, iconv -o, cpp, gpg -o, find -fprint, fallocate;
    eatmydata; busybox's sed -i and dd; a written startup file read by bash --rcfile, --init-file and -l, dash -i with ENV
    and zsh -i with ZDOTDIR; a pipe through rev, tr, envsubst, sed, awk or head into bash; `$(type -P cp)`, `$(realpath
    ..)`, `$(readlink -f ..)` and `$(basename ..)` as the command name; `> >(tee /dev/null | bash)`; python's popen,
    shell=True and an open on an operand or an environment name), each keyed on the shells measured writing; the prompt
    roads with a vanished operand, the deferred list's last item, measured refused since the tenth commit and pinned as
    rows. Every fix pinned by execution in the eleventh commit's rows test (93 rows, the writers measured in bash, zsh and
    dash), red on the tenth commit's head, and the record list on this header and decision 47 is derived by the plan test
    from the commits the hook's own text names, so a missing record for the newest commit reds.
    ROUND 6, TWELFTH COMMIT (2026-09-22; the round's two verifiers on the eleventh commit's head): three allows with a
    writer on no surface, each a reading fitted to its class now, members of stated classes filed, and a B2 boundary case
    named. THE SUBSCRIPTED POSITIONAL (mayVanish, positionalWords, candidateTexts): under zsh's grammar an unbraced
    `$argv[N]`, `$argv[-N]`, `$@[N]`, `$*[N]` or `$argv[N,M]` is an element or a range of the positional list, no field
    past its end, while bash and dash read a literal `[N]` after the parameter and the lexer marked the subscript so, so
    `$argv[1] cp a b` kept its head and copied in zsh while allowed (and so did the printer, here-string, sed and tee
    forms, `$@[1]`, `set --`, a function's body, eval, `zsh -c '..'` from every shell, the tracked notes/ folder, a cwd
    in no project and the operand road `cp $argv[1] a b`); where zsh may run the line the word may vanish, the walk's
    positional rewrite reads the element where it holds the list, and the head candidates carry the text with the
    subscript removed beside bash's reading. THE VANISHED HEAD TEXT (vanishedHeadTexts, scriptTexts' head role): a head
    word whose expansions the command never gives a value, glued to literal characters, stands for the text with them
    removed, one command the shell may run (`${c}cp a b`, `$c"cp" a b`, `"$c"cp a b` and the verifiers' `$argv[1]cp a b`
    copied while allowed, the first three at the round-5 head too); the empty text is kept only where headMayVanish says
    the whole word may stand for no field. The residual table's three glued-unset-head rows and its `$argv[1] $argv[2]
    $argv[3]` call are refused by name now and pinned as rows. THE STALE POSITIONAL CANDIDATE (scriptTexts' candKnown):
    bindPositionals notes each bind's values into the candidates and removes no earlier bind's, so after `set -- a;
    shift` the candidates still held `a` for `1` and `eval cp ${1:+x} a b` read the word alone and copied in every shell
    while allowed (and so did `shift 2`, a second `set`, `bash -c`, `sh -c`, `${1+x}`, `${@+x}` and `${*+x}` in bash, a
    head and every cwd); a positional's alternate value is read from the list the walk holds alone (posKnown, and vars,
    which bindPositionals rebinds), never from the candidates. THE BODY'S OWN LIST (the walk's set and shift): a `set` or
    `shift` inside a function body being defined rebinds the body's list, the call's, not this shell's (`f() { set -- a;
    }; eval cp ${1:+x} a b` copied in every shell while the body's `set` had bound `1` here). THE OPTION FLAGS
    (defaultWordReading's NEVER_EMPTY): `$-` is set in every shell but holds no flag in dash under `-c` (measured), so
    `${-:+word}` stands for nothing there and its dropped form joins the readings (`eval cp ${-:+x} a b` copied in dash
    while allowed), while `${-+word}` and the `#`, `$`, `0` and `?` forms keep the word alone. The residual table: 22
    rows added for a command substitution over a producer outside the output model handed to eval, a shell's -c or a
    here-string (an inner eval or shell -c, a call of a function, a written file read through the substitution, a value
    so made and run), the fifth class's gloss naming that conduit beside the pipe and the process substitution on every
    surface, and 4 rows removed as refused (268 rows over the same 8 classes). The B2 boundary (recordMutations): a path
    made from a source the resolver does not read is refused at the bound name while a project is in play; from a cwd in
    no project `cp "$(which cp)" <out>/scratch/c2; PATH=<out>/scratch:$PATH; c2 <proj>/base/report.md
    <proj>/docs/report.md` copies while allowed, an opaque operand after a literal head outside every project (the
    eighth class), pinned as a row with the shells that write. Every fix pinned by execution in the twelfth commit's rows
    test (114 rows, the writers measured in bash, zsh and dash), red on the eleventh commit's head.
    ROUND 6, THIRTEENTH COMMIT (2026-09-22; the round's two verifiers on the twelfth commit's head): three populations
    measured allowing while a shell writes, each pre-existing at the round-5 head and standing on no surface, filed on
    the residual table as rows keyed on evidence (the shells that write and the hook's verdict, re-measured every run)
    under one class named for the mechanism, a positional the resolver reads at the word by a model the shell does not
    keep, with no change to the hook; whether the class is fixed at the mechanism or accepted as allow-by-default is the
    round's ruling. THE EMPTY POSITIONAL (scriptTexts' posKnown): the colon form is read as set when the list the walk
    holds is long enough, never whether the element is non-empty, so `set -- ''; eval cp ${1:+x} a b` copies in bash,
    zsh and dash while allowed; 30 rows (a second or empty element, `bash -c`, `sh -c`, a double-quoted word or text,
    install, mv, `ln -f`, a redirection target, a subshell, a group, a list, a shift onto the empty element, a second
    set, `${@:+x}` and `${*:+x}` in bash and dash, the tracked notes/ folder, the project root, scratch/, a cwd in no
    project). THE STALE POSITIONAL CANDIDATE (candidateTexts, bindPositionals): each bind's values are noted into the
    candidates and none cleared, so after `set -- a; shift` a head word or a script text still reads `a` for `1` (`set
    -- a; shift; ${1}cp a b` is read as `acp`, no writer, while every shell runs cp; `eval "cp a ${1}report.md"` as the
    untracked `areport.md`); 31 rows (`$1cp`, `shift 2`, a second positional, `set --`, a double-quoted head, eval,
    `bash -c`, sed, tee, a pipe's or a process substitution's consumer, the eval, `bash -c` and `sh -c` script roads, a
    redirection target, notes/, the root, a cwd in no project, a PATH-bound name). THE KNOWN SET (scriptTexts' setKnown,
    candKnown and posKnown): a name's or the list's binding is read as this shell's where the shell does not hold it at
    the word, a value an `unset`, a `read`, a body's `local` or a reassignment to an empty default dropped, and a `c=a`
    or a `set -- a` in a subshell, a pipeline, a background job, a command substitution, an untaken if, `&&`, `||`,
    case, for or while body, a prefix position or behind `env`, `nice` or zsh's `command` (`c=a; unset c; eval cp
    ${c:+x} a b` and `(set -- a); eval cp ${1:+x} a b` copy in every shell while allowed); 31 rows, the shells named
    writing (bash and dash for a pipeline's last member and a background assignment, zsh for `command set`). THE
    SUBSCRIPTED POSITIONAL beyond one numeric index (ZSH_POSITIONAL_SUBSCRIPT, mayVanish): the regex takes one numeric
    subscript on the whole word while under zsh's grammar every `[..]` after the unbraced `$argv`, `$@` or `$*` selects
    from the list (`[@]`, `[*]`, an arithmetic, flagged or quoted subscript), and a word of several such expansions is
    not one subscript, so the head keeps its place and `$argv[*] cp a b` copies in zsh while allowed; 60 rows, zsh
    writing (every shell through `zsh -c`): the head, glued to the command, the printer, `zsh -c`, a function body,
    eval, sed, tee, `set --`, the operand road, notes/, the root, a cwd in no project. Three members of stated classes
    beside their witness rows (`$c printf -v x '..'; $x` in bash, `cat <(echo '..') | bash` and `f() { cat; }; echo '..'
    > >(f | bash)` in bash and zsh). The table's rows name their cwd where it is not docs/ (a sixth element); 423 rows
    over 9 classes, the class on every surface the property stands on, pinned by the plan test with the record and the
    count.
    THE RESIDUAL PROPERTY. The guard refuses a write only when it resolves the command to a writer it models (the
    writer cases of extract's switch, a write redirection, an interpreter's write call it scans) reached through a
    road it reads (the wrapper set, the shells' script roads, the readings of the resolver, the alias and hash roads),
    with a target it can place or cannot read. Every write that still reaches a tracked file is one the guard does not
    resolve to such a writer through such a road, whether or not its text stands in the command, and falls in one of
    these classes, each measured by execution in tools/romp-track-bash-guard.test.mjs (THE RESIDUAL TABLE, whose rows
    are the population this statement is over): a writer outside the model, a program, or a write form of a program
    the hook models, that writes the file by its own nature and is not among the write forms the hook reads (rsync,
    patch, tar -x, ed, ex, vim, make, shuf -o, gawk -i inplace, awk's print redirect, uniq, scp, openssl -out, shred,
    curl -o, wget -O, find -exec, a git alias or a subcommand that writes the tree, bash's history -w, zsh's sysopen
    and mapfile modules, sed's e command and a w command in a sed script the resolver cannot read, busybox's applets);
    a reader outside the roads, a program that runs a command or a script the hook does not follow into it (xargs, an
    interpreter's system, exec or subprocess call, a wrapper outside the set, a shell outside SHELLS, a file the
    command writes and then runs or sources, a function's call of itself, which the replay does not follow again); a
    command name the resolver never reads, a command whose name is an expansion of a kind the resolver does not read
    ("${a[@]}", a loop variable, a name read or filled by getopts, printf -v or a nameref, a name the shell itself sets (${SHELL}, $0, $BASH, $ZSH_ARGZERO, $_ after a command), a substitution
    outside the output model such as $(which cp), a ${...} operator form the resolver does not read, a positional
    parameter of a script handed to a fresh shell with arguments of its own; "$@", $1 and $* stand for the operands of
    a called function or of a `set` this shell ran since round 6's sixth commit); a script held in a variable, a value
    the command gives a name through a construct the resolver does not read (`read`, `printf -v`, a positional
    parameter of a fresh shell's script), run as a command or handed to a shell (`$c` after `read c`, `eval "$1"`
    inside a `bash -c` given arguments, `bash -c "$c"` after `printf -v c`; a value an assignment word gives,
    whitespace included, is read through THE HEAD CANDIDATES since round 6's fourth commit, and a `${name:=word}`
    gives word since the sixth); a producer outside the output model, a pipe into a shell, or a write redirection into a process substitution running one, from anything but a literal
    echo or printf, alone or in a subshell or group of such commands, or a plain cat passing such a text through, or a
    command substitution over such a producer handed to a shell, an eval or a here-string (a call of a function the
    command defines, a tee or a pipe through another command, a cat of a file, an eval or a shell -c inside the
    substitution); zsh's glob grouping, a `(..)` inside a word handed to zsh, read as a subshell by the lexer's zsh
    grammar while zsh globs it (a lexer gap, stated since the first commit of this round); zsh's hook functions, a function the command defines under a name zsh calls on its own (chpwd, precmd, preexec, periodic, zshexit, and the names in chpwd_functions and its kin), whose body runs when the shell moves, prompts or exits, from the directory the shell is in then, while the guard judges the definition where it stands; a positional the resolver reads at the word by a model the shell does not keep, an element's emptiness, a binding a later shift or unset removed, zsh's subscript grammar beyond one index (the colon form of a positional's alternate value is read as set by the list's length, not the element, so `set -- ''; eval cp ${1:+x} a b` copies in every shell; a head or script text reads a positional's candidate that no shift, second set, unset, read or body's local removes, so `set -- a; shift; ${1}cp a b` is read as `acp` while every shell runs cp, and the known set reads a name bound in a subshell, a pipeline, a background job, a command substitution, an untaken body, a prefix position or behind a wrapper as this shell's, as in `c=a; unset c; eval cp ${c:+x} a b`; the unbraced list's subscript is read as one numeric index while zsh's `[@]`, `[*]`, an arithmetic, flagged or quoted subscript and a word of several such expansions select from the list too, so `$argv[*] cp a b` copies in zsh, and in every shell through `zsh -c`; each pre-existing at the round-5 head and filed in round 6's thirteenth commit for the round's ruling, a fix at the mechanism or an accepted allow); an opaque expansion from a cwd outside every project,
    a leading opaque expansion, or one after a literal head outside every project, from a cwd in no project (B2 as
    ruled, with its boundary). A shape outside these classes that reaches a tracked file is a rule to state, not a
    residual.
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
    when it is missing and removed again when nothing else landed in it.
    A writer is dead when `kill(pid, 0)` answers ESRCH, and a pid is judged only by a reader in the pid namespace that
    stamped it: pids are per namespace, and from a child pid namespace (a sandboxed tool shell with one of its own,
    bubblewrap's `--unshare-pid`) every process outside is ESRCH, alive or not, while a pid stamped inside one names,
    outside it, whatever process has that number there. Judged by pid regardless (the slice's review, third and fourth
    rounds, 2026-09-11), a CLI in such a sandbox read the host's live lock as a dead writer's, broke it at once and
    wrote inside the host's load-to-rename; and the host read the sandboxed CLI's live lock so whenever the CLI's pid
    inside was a free number outside, broke it and wrote inside the CLI's load-to-rename, the loss this decision
    closes, back for every such session. So a writer outside the initial namespace names its own on a second stamp
    line, `ns <inode>` (the inode of `/proc/self/ns/pid`; the initial namespace has one inode number on every Linux
    and is named by the line's absence), a reader judges the pid only when the lock names the reader's own namespace,
    and any other lock is judged by its stamp's age alone: a dead writer's fresh lock from another namespace holds
    every waiter until the stamp is 15 s old, each refusing as held at the end of its 2 s wait before then. Where
    `/proc` cannot be read, a process is taken to be in the initial namespace. A stamp more than 15 s from the
    reader's clock in either direction is a dead writer's (judged by age behind alone, a `.lock` committed from a
    machine whose clock ran ahead, or planted, with a pid alive here held every writer of that file to `busy` for as
    long as its stamp stayed in the future; a clock stepped back that far mid-write breaks a live lock, as a step
    forward already did). `tools/store-io-lock-clock.test.mjs` drives that: a lock stamped `1 <an hour ahead>` is
    broken at once, pid 1 alive to every reader or not, a live pid's lock stamped five seconds ahead is waited behind,
    a stampless lock's mtime is judged the same way, a dead breaker's claim an hour ahead beside a dead lock is
    removed and the break proceeds, and the real `track-comment` against such a lock lands its comment and exits 0 in
    well under the wait (the fourth round). A lock written from another machine over a shared filesystem names a pid
    of that machine, which this one judges as its own, dead when no process here has the number and else by the
    stamp's age; the lock serializes the writers of one machine (`tools/store-io-lock-pid-namespace.test.mjs`, the
    namespace read through a stand-in so the cases run on any machine, and one real child namespace where `unshare`
    can make one unprivileged, skipped where it cannot).
    The break has one winner (the slice's
    review, first round, 2026-09-11; as first built two waiters that read one dead lock together both removed it,
    the second taking away the first's fresh lock, and both wrote): the waiters that find a stale lock serialize
    on a claim beside it, `<sidecar>.lock.break`, created with O_EXCL like the lock and holding the same `pid ts`;
    the one holding the claim judges the lock again under it, unlinks it only while it is still stale, and removes
    the claim on its way out; a claim whose breaker is dead or whose stamp is past the bound is removed by the
    lock's own rule.
    The entry judged stale, lock or claim, stays open from the judgment through its unlink (the third round: judged by
    inode number alone, the guard was defeated by the filesystem's reuse of the number, an unlink and then a create in
    one folder handing the new entry the number just freed, so a breaker suspended past the stale bound between its
    claim check and its look for the unlink removed the fresh lock a waiter had put at the name and entered beside
    it); an inode with a descriptor open keeps its number, so the fresh lock is another inode and is left alone
    (`tools/store-io-lock-inode-reuse.test.mjs`: one interleaving driven by hand in-process, and a breaker child
    stalled past the bound at its look while a real writer breaks its claim and the dead lock, writes and leaves, the
    breaker waiting for that write instead of entering beside it).
    The release unlinks the lock only while the entry at the name is the holder's own inode, so
    a writer broken as stale while alive leaves the breaker's lock alone; a stamp that cannot be written after the
    create leaves no lock and no folder behind; a writer that made the folder and leaves while another writer's
    lock or claim is in it passes the folder's removal to that writer by a `made-dir` line appended to its lock or
    claim, honored at that writer's release (or by the breaker of that lock when its holder dies); and a link or
    another non-file at the lock's name, or at the claim's while a stale lock stands, is a lock that cannot be
    taken: the host refuses `unreadable` naming it, the CLIs print its line and exit 1, and nothing is followed or
    removed.
    An entry at the folder's name that is not a directory (a link to nothing above all: the create says ENOENT through
    it and `mkdir` EEXIST at it, on every turn) is refused the same way, at once and naming the entry, the CLIs
    printing its line and exiting 1 in well under the wait; a link to a directory the lock follows, the folder behind
    it staying, where the host refuses any entry there that is not a directory itself, a link to one included, as
    `unreadable` before it locks (`checkTrackDir`). Retried until the wait ran out, such an entry was reported as a
    live writer where there was none (the third round; `tools/store-io-lock-folder-name.test.mjs`).
    The two names and that line are everything the lock leaves under `.trackchanges/`
    (`tools/store-io-lock.test.mjs`; the ADR's lock bullet, `docs/adr/0002`, is held to the same names and line
    and to the lock run in a scratch root by
    `tools/0002-file-comments-in-the-track-changents-sidecar-lock-names.test.mjs`). `track-edit`, `track-comment`
    and `track-reply` take it around their load-to-rename (`track-edit` from the file read through the file write and
    the edit turn it adds to the comment it answers) and, when it is not obtained, print `another editor is writing this file; retry` and exit 1
    with nothing written; their `fail()` throws to the entry point so a held lock is released. That part is
    vendor patch 0008, written as offerable to the engine's author and held back from the offer by the
    standing word of 2026-09-11 to open nothing new upstream.
    The vendored README's row for it names the lock's whole footprint on disk, the two names, the line and the folder,
    held to `store-io.mjs`'s constants, to the patch header and to the ADR bullet by
    `tools/README-track-changents-patch-0008-row.test.mjs` (the third round, which found the row naming the lock
    alone).
    The host takes the same lock from its fence stat through its
    last rename or prune (`underStoreLock`): the sidecar's for `comment`, `reply`, `resolve`, `retarget`,
    `accept`, `reject` and `save`; `config.json`'s own for `set-tracked`, since that verb writes the root's list,
    which every file under the root shares, and a held `config.json` lock refuses `busy` naming the root's tracked
    list rather than the file, since that is what the lock guards (`tools/file-comments-host-config-lock.test.mjs`).
    The decisions load under it too: `loadForDecision`, the fence stat, the file read and the sidecar load, runs
    inside the function `underStoreLock` runs (`tools/file-comments-host-decision-lock.test.mjs`: against a holder
    that saves a comment 300 ms later, a reject-all, an accept and a save each refuse `store-moved` and the retry
    lands both; the fourth round, which found no module saying where a decision's load sits).
    A loose file takes it after its landmark and checks its `""` fence
    again under it, and every reply is built after the release from a store read back under the lock. The mtime
    fences stay: the lock serializes the writers, the fences catch the panel's stale copy, so every writer loads
    after the previous writer's rename and a stale copy always refuses. A lock still held after the wait refuses
    `busy` with nothing changed; the panel handles `busy` as it handles a moved fence (`MOVED`): a fresh status,
    one retry by id (the id-less verbs re-read and say nothing was decided), and the refusal verbatim with Reload
    on a second.
    `busy` arrives while the other writer still holds the lock (every holder releases after its last rename, and
    `status` takes none), so the fresh status shows that writer's store only when it renamed in the gap, and the retry
    otherwise goes out on the fence the refusal came back on; a holder that finishes under the retry moves the fence
    and the host refuses `store-moved`, the second refusal, shown with Reload and not retried
    (`ui/webview/file-comments-busy-retry-fence.test.ts`, the save path at the real timing; the third round, which
    found the panel's comments saying the holder's write was on disk at the refusal).
    `tools/file-comments-host-store-lock.test.mjs` drives the host and `track-reply` against a
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
    record by name, and both records to the glossary's words for a file and a comment, and
    `tools/file-review-plan-sidecar-lock-modules.test.mjs` the third round's five modules (every
    `tools/store-io-lock-*` and `tools/README-track-changents-patch-*` module, and the busy retry's) to the Tests
    bullet and to this record by name, what the bullet says of each to the module, and this record's pid-namespace
    sentences to `store-io.mjs`.
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
51. **A recurring passage's copy is confirmed by its ordinal, then by its heading path, before the position's
    nearest copy is guessed** (2026-09-11). The user reported a comment on a passage that occurs more than once
    painted as a guess: the anchor matched several copies with the same surroundings, and the position stored
    with the comment named none of them as the file stood, so the copy nearest that position was highlighted,
    dashed, with the "passage recurs" tag. The cause was a change to the file the host never recorded (a raw
    write outside the tracked path, since closed by decision 47's Bash guard; an editor save): the refresh moves
    a position only where the recorded changes vouch for the copy, and an unrecorded edit above moved every copy
    past the stored position at once. The user said yes to breaking the tie from what the comment itself
    records. The host writes three more romp-only fields beside `anchorAt` on a passage comment, at creation and
    on every host write for a comment whose position names its copy: `ordinal`, the 1-based index of the copy
    among the whole anchor's matches at that moment (1 when unique); `copies`, how many matches there were then;
    and `section`, the heading path above the passage, the text of the nearest preceding markdown headings from
    the top level down joined with " > ", empty for a file without headings or a non-markdown file. Each heading's
    text in the path is cut at 200 characters (`SECTION_HEADING_CAP`, by code point, at the stamp and the read
    alike, so two headings alike for that long are one path; the review's first round, 2026-09-11, after nine
    comments under a heading line of a megabyte refused every write as `too-large`), the headings are read as the
    viewer renders the file (a leading BOM, CRLF line ends, a front-matter block by the viewer's own test in
    `md-config.ts`), and whether the file is markdown is judged from the file's name, `.md` or `.markdown`, at
    every stamp and every read, never from the sidecar's own `path` field (the same round: the refresh had
    judged by that field once, stamped an empty path on a markdown file, and a later read took the empty path
    for the copies above every heading and confirmed one of those). When the
    host must choose among several copies and the position names none, not even by the quote with one side
    of its context whole beside it (`locateStored`, which every reader of a stored anchor in the host goes
    through, and the `placed` map every reply carries for the panel), the rules run in order: the count of copies unchanged since the fields were
    written, the ordinal's copy, confirmed, unless the stored heading path names other copies and not the
    ordinal's, when the two fields disagree and the tie is a guess (the review's third round, 2026-09-11, said
    below); else, the count changed, exactly one copy under the stored heading path, that copy, confirmed; else
    the copy nearest the position, a guess, as before. The panel paints a confirmed copy plainly (no dashed cue, no tag) and a
    guessed one as before, for a passage comment with the card's words now ending "Reveal it and save again from
    the right copy to confirm." and for a region comment with the card's words ending in the recourse a region
    has, said below. A passage comment's guessed copy has its card offer the Reveal those words name (the review's
    first round: before it the card offered Reveal only for a passage it could not paint, so the words named a
    button the card did not have); it switches to Raw and scrolls to the guessed copy, and its title says that a
    comment saved from the copy you mean is placed on that copy and this one keeps its tag until you resolve it,
    which is what the guide says of saving again (a new card on that copy with no tag; the old card keeps its tag until you
    resolve it; `tests/test_guide_files_comments_confirm.py`). A confirmed place the view's text has moved past
    (the poll's reload paints before the fresh status lands; a refused refresh keeps the old status) paints the
    copy nearest that place as a guess whose words name the confirmed place (`confirmedAt`), never plainly on a
    copy the host did not vouch for in the text shown. The viewer's own sequential hint comes last, after the confirmed
    copy and the stored position (plans/markdown-viewer.md, Slice 5 item 7: a card with neither whose anchor an earlier
    card of the paint pass shares is painted on the copy after that card's, `nextCopyHint`, and its words name that copy,
    `hintedCopy`).
    A region comment on an embed line that recurs is guessed by the same rules (the host stamps and places every
    anchored comment, and the panel's `copyUnsure` asks the same of a rectangle, which `paintRegions` puts on the
    figure nearest the hint by `regionImageFor`), but the passage's recourse is not open to it: Reveal for a
    region scrolls to its picture and never switches to Raw, and Re-place sends the rectangle alone, so the host
    keeps the anchor, its position and its copy fields (`doRetarget` writes `target` back and nothing else), and
    the one thing that places a comment on the figure meant is a new region drawn on it, with a mouse. Its words
    end with that in place of the Reveal sentence (`REGION_CONFIRM`: draw a new region on the figure you mean, and
    this comment keeps its tag until you resolve it; Re-place redraws the rectangle on the figure shown and does
    not move the comment to another figure; drawing a region needs a mouse), and its card offers no Reveal: Reply,
    Resolve and Re-place on a pointer that draws, Reply and Resolve on a coarse one, where the words naming the
    mouse keep the card from dead-ending (the review's second round, 2026-09-11: before it the region card wore a
    Reveal titled for the Raw view that scrolled to the picture already framed, over words asking for a save a
    region cannot make). The same round put what the passage's save does on the open card as a line of its own
    under the words that ask for it (`SAVE_FROM_COPY_NOTE`, the sentence the Reveal's title carries), since a
    button's title never reaches touch; a region's words carry their own.
    `ui/webview/file-comments-tiebreak-region.test.ts` drives both card kinds over the rendered stand-in and a Raw
    body, `tools/file-comments-host-tiebreak-review-2.test.mjs` the round's findings on the host, and
    `tools/file-review-plan-tiebreak-review-3.test.mjs` holds this account of the round to the panel, the host and
    the tree (the Tests section says what each drives).
    The review's third round (2026-09-11) qualified the first rule, the position's, and the reply's map. The
    ordinal's copy is confirmed where the stored heading path names no copy at all (a heading renamed or deleted
    above the copies; a non-markdown file, whose paths are all empty) or names the ordinal's copy, among others or
    alone; where it names other copies and not the ordinal's, the two fields disagree, neither confirms, and the
    tie is a guess: an unchanged count does not say that no copy was added or removed (one copy deleted and another
    pasted under a different heading keep the count and move the ordinal onto a copy the person never commented,
    which the round found confirmed and painted plainly), a heading moved among the copies misleads the heading
    path the same way, so a tie the two fields read two ways is left to the person, and the section rule runs
    once the count has changed. The contract the user said yes to confirmed the ordinal's copy whenever the count
    was unchanged, with no such condition; the code and this record hold the qualified rule, and the user's word
    on it is open (Open questions). A position the quote sits at with ONE side of its context whole beside it, the
    other side edited (the state the refresh leaves when a recorded change edited the chosen copy's context and
    not its text, and the state a raw edit of the surroundings alone leaves), names the passage before any rule
    runs (`quoteSitsAt`), the copies whole elsewhere being the other copies: before it the rules ran over those,
    and a tracked edit inside the first of two copies under one heading had the section rule confirm the second,
    which the panel painted plainly while the reply's own `anchorAt` named the first. The third round took the
    quote alone; the review's fourth round (2026-09-11) asks for the one side, since a bare occurrence of the
    quoted words (a passing mention, a table cell, one character of a run) is what a stale position lands on by a
    coincidence of distance, a raw insertion above of exactly the gap to it, and the quote alone took the comment
    off the copy the fields named for the mention. The reply carries no verdict for such a comment, and the panel
    paints by its own engine, which scores a whole copy over an edited one: with three or more copies the nearest
    whole copy as a guess with its cue, the cue from before the tie-break; with exactly two, the one still whole,
    plainly, the paint of the anchors follow-on, on the copy the person did not comment, since the map's contract
    (a tie the position names no copy of) does not carry a position verdict today
    (`ui/webview/file-comments-host-tiebreak-review-3-panel.test.ts` drives the panel's half). While every change
    to the text is on record (the text is as the sidecar's last writer left it, so the pending changes are the
    whole difference), the reply's map forwards a tie's verdict only where the recorded changes carry the stored
    position to that very copy (a tracked insertion above moved every copy alike) or to no one place, and drops
    one they carry elsewhere (`placedFor`, `carriedTo`), since the next write's refresh moves the position there:
    between a session's edit inside the first of two copies and the next host write, the status had confirmed
    the second copy by section from a position two characters stale that the recorded edit accounted for. After
    a raw write the changes vouch for nothing and every verdict is forwarded, as before. The walk over the copies
    the recorded changes can have carried a position to (`reachable`, for the refresh and for `carriedTo`) reads
    the changes off one sorted index, a compare per change to build it and a compare per copy inside the changes'
    window, charged to the budget; a walk that does not fit is nothing known, the refresh keeping the position and
    counting the comment among the unscanned, the map forwarding the verdict (the fourth round: uncharged and
    summing every change per copy, the walk held a status on ten thousand pending changes and twenty stale tied
    comments 18 s). Two more corrections
    from the round: creation writes no copy fields for a passage whole at more places than the refresh
    enumerates (`REFRESH_COPIES_MAX`), as the stamping pass already refused to (before it the cap itself was
    written as the count, and a later text of exactly that many copies had the ordinal rule confirm from a false
    count); and the front-matter reader closes a block on `---` alone, as the viewer's test does (a block closed
    only by YAML's `...` is body, and a heading in it is the passage's path; before it such a heading was shown to
    the person and absent from the stored path). The section rule and the nearest pick read the matches grouped
    by heading path once per anchor and by binary search (`copiesUnder`, `nearestOf`), so a status on thousands
    of tied comments sharing one anchor stays inside the kernel's deadline. On the panel's side the recourse is
    worded for what the render shows: with the editor up (Slice 5) no highlight of ours is painted and the card
    offers neither Reveal nor the composer, so a guessed card's words say only that the copy is a guess and name
    the way there first, leave edit mode, then reveal it and save again from the right copy (`UNSURE_IN_EDITOR`,
    `PASSAGE_CONFIRM_AFTER_EDIT`; a region's, leave edit mode, then draw a new region in the view that shows the
    image, `REGION_CONFIRM_AFTER_EDIT`), a passage's save line standing under them as in the read view, and offer
    no Reveal; a region whose picture the view does not show (Raw) is told which view has it
    (`REGION_CONFIRM_UNSEEN`); and a pictured region's card on a coarse pointer, where no overlay takes a drag and
    the card offers no Re-place, ends with the pictured view's words less the sentence about Re-place
    (`REGION_CONFIRM_TOUCH`; the sweep after the round, the same day). Before them the card in the editor named a
    Reveal and a save it did not offer, the Raw card said to draw on a figure the view did not show, and the
    phone's card named a Re-place it did not have. `tools/file-comments-host-tiebreak-review-3.test.mjs` drives
    the round's findings on the host, `ui/webview/file-comments-host-tiebreak-review-3-panel.test.ts` the panel's
    half of the position the quote names, `ui/webview/file-comments-tiebreak-shown.test.ts` the words over the
    editor and Raw, `ui/webview/file-comments-tiebreak-touch.test.ts` the words on a coarse pointer, and
    `tools/file-review-plan-tiebreak-review-4.test.mjs` holds this account of the round to the host, the panel
    and the tree (the Tests section says what each drives).
    The contract named two fields; `copies` is the third,
    since the first rule compares the count of
    copies with the count at the time the ordinal was written, and the ordinal alone does not carry it. Setext
    headings (a line underlined with `=` or `-`) are not read as headings, a tie with no position still refuses
    `anchor-ambiguous` when neither field tells (the fields settle it as for any other comment, so one whose
    position an editor dropped is confirmed from its ordinal or its heading path, and a comment the CLI made on
    a passage that recurs with the same 24 characters around it (the context the CLI stores) carries neither and
    is refused as before; no host write stamps it while the tie holds, since the refresh stamps only a comment
    it seats and never seats a tie with no position, and the next host write after an edit leaves its passage
    at one place seats and stamps it, as it stamps a CLI comment on a unique passage, which was never refused;
    the review's second round, 2026-09-11, which found this record saying the next host write stamped it), and
    the other editors write the object back whole, so the fields survive them (docs/adr/0002: six additive
    fields now). Tests:
    `tools/file-comments-host-tiebreak.test.mjs`, `ui/webview/file-comments-tiebreak.test.ts`,
    `ui/webview/file-comments-tiebreak-browser.test.ts` (Chromium and Firefox: the same paragraph twice under
    different headings, a comment on the second, a paragraph inserted above by a raw write, the status refreshed,
    the highlight on the second copy with no tag), `tools/file-review-plan-tiebreak.test.mjs`,
    `tools/file-review-plan-tiebreak-review.test.mjs` (the review's two corrections to this record: the stamp's
    pass on a passage still at its position, and the fields settling a tie with no position),
    `tests/test_guide_files_comments_anchors.py`, and from the review's first round
    `tools/file-comments-host-tiebreak-review.test.mjs` (the real host: the heading path read as the viewer
    renders the file, the file's kind from its name, the nearest fallback off the enumerated matches inside the
    kernel's deadline, the stamping order and its note, the engine-placed stamp and `placed` on every write's
    reply), `ui/webview/file-comments-tiebreak-recourse.test.ts` (the guessed card's Reveal, the confirmed place
    the view moved past) and `tests/test_guide_files_comments_confirm.py` (the guide's sentence on saving again,
    walked on the real host); from its second round, `tools/file-review-plan-tiebreak-review-2.test.mjs` holds
    this record's account of the first round to the code; from its third round,
    `tools/file-comments-host-tiebreak-review-3.test.mjs` (the real host: the position the quote names with one
    side of its context, the recorded window's dropped verdict, the ordinal's yield, no copy fields at creation
    past the cap, front matter closed on `---` alone, a status on thousands of tied comments inside the deadline),
    `ui/webview/file-comments-host-tiebreak-review-3-panel.test.ts` (the panel's half of that position),
    `ui/webview/file-comments-tiebreak-shown.test.ts` (the words with the editor up and in Raw),
    `ui/webview/file-comments-tiebreak-touch.test.ts` (the words on a coarse pointer) and
    `tools/file-review-plan-tiebreak-review-4.test.mjs`, which holds this record's account of the third round to
    the code.
52. **An inline start tag with no end tag in its block renders as literal text, and the anchor map places it**
    (2026-09-18). The user reported that comments from the Rendered view were refused over most of one of their
    notes. The assessment of 2026-09-18 traced every refusal to one inline tag: a placeholder written mid-paragraph
    as a `<table>` start tag followed by a file name (the tests write it `(<table>__widths.csv)`). marked lexes such
    a tag as an inline `html` token and passes it through; DOMPurify parses the viewer's HTML without a doctype, and
    in that quirks-mode document a `<table>` start tag closes no open `<p>`, so the table opened inside the
    paragraph's element and the next heading, paragraph and table were parsed into it. The anchor map predicted no
    text for an inline html token and pairs blocks with top-level elements one for one, so the paragraph was refused
    as not matching the file and every later block met the element three places on: 150 of the note's 189 blocks
    refused, identically on every main head since the map's first release (the fork's PR 277), so a long-standing
    gap and not a regression. The same shape lost content silently: after an inline `<title>`, `<script>`,
    `<style>`, `<xmp>`, `<iframe>` or `<plaintext>` start tag in prose, the parser took the rest of the note as the
    element's text and the sanitizer dropped it; after a `<template>` the parser put the rest into the template's
    content, which the browser renders nowhere (the sanitizer keeps the element); after a `<textarea>` the rest
    showed as unformatted characters, the element dropped and its text kept (each shape run over the base tree in
    the review of the slice's PR, round 1). The user took the assessment's first
    option on its recommendation: such a tag renders as its own characters, and the map predicts them.
    The rule: an inline `html` token that is a START tag of a non-void element, with no matching end tag later in
    the SAME block's inline tokens, becomes a `text` token in place, its raw kept and its text the raw escaped as
    marked's inline text tokenizer escapes text, so marked's text renderer writes `&lt;table&gt;`, the reader sees
    `<table>`, and the map's `text` case places the characters at the raw's position, with no new branch on either
    side (the installed marked 12's `Renderer.text` writes a text token's text as is, and its `Tokens.Text` has no
    `escaped` field, so the text is escaped up front: `<`, `>`, `"` and `'` always, `&` unless it begins a character
    reference). Matching is by element name, ASCII case-insensitive, innermost first: a stack per name of the open
    start tags over the block's inline tokens flattened in document order (a tag inside emphasis, a link's label or a
    highlight counts), an end tag popping the latest open tag of its name and no other, so `<b>x<b>y</b>` keeps the
    inner pair as HTML and makes the first `<b>` text, `<B>x</b>` is closed and `<b>x *y</b>*` is closed through the
    emphasis. The stacks date from the review's first round (2026-09-18): the first build kept one list of every
    open start tag and scanned it from its end on each end tag, quadratic when thousands of stray end tags followed
    thousands of open start tags of another name, seconds of blocking work twice per open (the viewer's parse and
    the map's lex); the stacks are linear in the run's tags and convert the same tokens, held against that list as
    an oracle over a fixed sample and a seeded random one. The block is
    the token that owns the inline run, each on its own: a paragraph, a heading, a tight list item's text, a
    footnote definition, a table cell; a list, a quote and a callout are walked into for the blocks they hold.
    Everything else is left as lexed: a start tag closed within its block (`<b>x</b>`, `<span class="a">y</span>`,
    `<kbd>Ctrl</kbd>`), a void element, the `image` start tag (below), the self-closing syntax `<x/>`, an end tag (a
    stray one keeps `blockEnds`' reading), a comment, a processing instruction, a declaration and a CDATA section;
    block-level `html` tokens are not read (the tag scan, `topTags`, models what the parser makes of an html block).
    The void list is HTML's fourteen, `VOID_ELEMENTS` in the module: `area`, `base`, `br`, `col`, `embed`, `hr`,
    `img`, `input`, `link`, `meta`, `param`, `source`, `track`, `wbr`; anchor-map.ts's `VOID_TAGS`, which its tag
    scans read, is that same set, so the rule and the scans share one list. One start tag outside that list is left
    HTML too (the review's first round, 2026-09-18): `image`, the obsolete alias the HTML parser's in-body insertion
    mode rewrites to `img` as it inserts it, so `<image src="a.png">` in prose opens nothing and the browser draws
    the picture, as it did before the rule; `IMG_ALIAS` in the module, a constant of its own and not a fifteenth
    void element, because inside an inline `<svg>` an `<image>` is an element with an end tag of its own and the
    map's tag scans, which read `VOID_TAGS`, read it so. The other start tags the parser inserts and pops at once
    beyond the void set (`keygen`, `basefont`, `bgsound`) fall to the rule and render as text: the sanitizer drops
    those elements with nothing shown, and this record prefers the characters shown. The self-closing flag is read
    as the HTML tokenizer reads a tag (`isSelfClosingTag`, the same round), attribute by attribute: a quoted value
    runs to its closing quote, an unquoted value to the next blank or `>`, and the flag is a `/` right before the
    `>` outside them all. So `<a href=http://a.test/>` is an open start tag, the `/` the unquoted value's own last
    character, and with no end tag in its block it is text; the first build's suffix test on the raw (`/>` at its
    end) read that tag as self-closing and left it HTML, and the browser opened the `a` and wrapped every later
    block in it, the shape the rule exists to stop.
    One rule in one code path is the design point that keeps the risk low: one module,
    `ui/webview/md-literal-tags.ts`, exports `literalizeUnclosedTags(tokens)`, and two callers run it on their own
    token trees of the same source under the one configuration (md-config.ts), so both convert the same tokens and
    no wrong anchor can result. The
    viewer's `mdBlock` (file-view.ts) calls marked.parse's three steps apart: marked's lexer, the rule, the
    walkTokens it ran inside marked.parse (the fence collection, `viewerWalkTokens` for the file kind, the defaults'
    walk, unchanged and in the same order) and marked's parser, over a copy of the singleton's defaults as
    marked.parse copies them, on THIS parse's tokens alone. Nothing is registered on the singleton (no marked.use,
    no renderer hook; the module imports marked's types alone), so the chat's `md()` (render.ts, still marked.parse)
    and md-config.ts are untouched and the feed renders as before. The map's `placeTokens` (anchor-map.ts) runs the rule
    on the lex line, after `Lexer.lex` and before anything reads the tree, so the text walk, `tagOf`, `topTags`,
    `blockEnds` and the pairing never meet the converted token as html; the `open` array `blockEnds` collected (the
    formatting tags a paragraph left open, whose wrapper element the pairing did not model, recorded under Slice 5
    of plans/markdown-viewer.md with the `Block.leaves` fix shape and routed to Slice 8, which did not build it) can
    therefore hold nothing but an unclosed `image` start tag, the one start tag the rule leaves HTML that the scan's
    void set lacks, which opens no element in HTML content (the parser rewrites it to the void `img`; inside an inline
    `<svg>` the `image` element is closed by `</svg>` and every block still maps), or a start tag written inside an
    html comment (`<!-- an aside <b> -->`: the scan's `TAG_RE` reads the comment's raw, the rule's scan does not), which
    the parser reads as part of the comment; neither opens an element around the later blocks. The SELF-CLOSING
    spelling of such a tag still does: the rule leaves it HTML (`isSelfClosingTag`) and the scan reads it as a leaf,
    but the parser ignores the flag on an HTML element and opens it, so `<b/>` in prose is a wrapper around every
    later block (the tag's paragraph maps and every later block is refused with the mismatch sentence), `<div/>` a div
    holding them, `<table/>` one paragraph holding them, and `<title/>` takes the rest of the note as its text, which
    the sanitizer drops (`ui/webview/anchor-map-literal-tags-browser.test.ts` records each in the real pane, the same
    shapes and verdicts over the base tree; `ui/webview/anchor-map-literal-tags.test.ts` records `<div/>`, `<table/>`
    and `<title/>` over its stand-in, which does not model the `<b/>` wrapper); the pairing does not model that
    wrapper, so the fix shape recorded for it, `Block.leaves`, is NOT moot: before this decision the bare `<b>` with no
    closer made the same wrapper, and the rule removed it for that spelling alone (the review of the slice's PR, round
    1, 2026-09-19). The map passes the scan a fresh array and reads it nowhere.
    Deliberately left, recorded here: `<hr>` inline is void, stays HTML and still splits its paragraph in the
    parser; a start tag whose end tag stands in a LATER block renders as text now, and the later block's end tag is
    a stray, where the parser used to wrap the blocks between in its element; a block-level element closed within
    its block mid-line (`<div>x</div>`) still splits the paragraph in the parser, a known gap; marked's inline lexer
    state is not rewound between blocks: one Lexer lexes every block's inline run in turn, so a flag one block sets
    stays set for the rest of the document. After an unclosed `<kbd>`, `<pre>`, `<code>` or `<script>` it lexes the
    remaining text of that block and of every later block unescaped (`inRawBlock`), until an end tag of any of those
    four names (a stray `</code>` closes an open `<kbd>`) or the document's end. Under the flag marked's inline tag rule
    still reads a tag-shaped run (`<c>`, `<c a="b">`, `<y z>`, `<y then d>`) as an `html` token, so the rule and the
    parser treat it as in any block: with no end tag in its block it is converted and its characters show and map;
    closed (`<c>x</c>`) it stays HTML. A `<` before a letter that the tag rule does not read as a tag (`<b=c>`, `<b/x>`,
    `<y z t2.` with no `>` after it in its block) is unescaped text, and the browser's parser reads a tag from that `<`
    to the next `>`, the block's own end tag when the block's text has none: those characters are gone from the rendered
    view and the block is refused with the mismatch sentence. What else the parser makes of it depends on the name it
    read: `<b=c>` and `<y/x>` leave no element on the page and the next block maps; `<b/x>` (read as `<b x="">`) and
    `<div/x>` open an element that holds every later block, the wrapper the self-closing spelling opens above, and those
    blocks are refused when two or more stand in it (one alone inside a formatting element still maps, as it does after
    `<b/>`; after `<div/x>` it is refused); a heading whose own end tag was read as the `>` stays open, and the next
    block is parsed into it and refused too. After an unclosed `<a` it autolinks no bare URL in that block
    or any later one (`inLink`), until an `</a>`. Both as before: the rule runs after the lex and changes no lexer
    state, and main's path lexes the same. Left too, found in the review's consolidation pass (2026-09-18): a heading
    holding such a tag (`## Results <b>`) takes its id from its rendered text, the tag's characters included
    (`mintHeadingIds` in file-view.ts slugs the sanitized heading's textContent, and a converted token is a text token
    like any other, so nothing there tells the tag's characters from typed text): `md-results-b`, where GitHub's slug
    of that heading, which reads the tag as HTML, is `results`, so the note's own `[..](#results)` link and an open at
    `#results` miss it (the open reports no section of that name; the Outline, which lists the rendered headings
    themselves, still lands). Before the rule the same heading was slugged `results` and its open `<b>` bolded the
    rest of the note. A fix would slug the heading's inline tokens with the converted ones skipped, a second slug path
    for a heading that holds an unclosed tag and is a link's target at once; the user decides whether it is worth one
    (`ui/webview/md-literal-tags.test.ts` holds the shape and the slug). Left too, found in the review of the slice's
    PR (round 1, 2026-09-19): a converted tag's own id or name is no longer a fragment target, since the tag is text
    and no element. An unclosed `<a name="spot">` or `<span id="sid">` written mid-prose reached the DOM before as an
    element under the sanitizer's `user-content-` prefix, so the note's own `[jump](#spot)` landed on it (the link's
    title `Go to spot`); it is characters now, so that link is dead, with the title `No heading or anchor named
    “spot” in this document` (`linkMarkdownAnchors` in file-view-links.ts finds no target), where the open `<a>` before
    also stayed open past its paragraph: the browser's parser reopened the `a` after it and kept it open until the block
    holding the note's next `<a>` or `</a>` tag, or to the end of the note when none followed, and the map, which pairs
    blocks with top-level elements one for one (above), lost the count unless the reopened `a` held exactly one block (a
    paragraph, a heading, a list, a table, a fenced code block or a blockquote between the tag's paragraph and the link:
    every block mapped). With no later `<a>` it wrapped every later block, a heading, a list and a table included, and a
    selection in any of them was refused with the mismatch sentence; with the `[jump](#spot)` link in the next paragraph
    the link's own `<a>` closed it holding nothing but a line feed, an extra top-level element, so a selection in that
    paragraph or in any after it was refused, in the last with `The selection could not be matched to the file text.`:
    the shape the rule exists to stop. Untouched, landing before and after: a closed tag (`<a name="x"></a>`, the README
    idiom, mid-prose or on its own line) and a tag alone on its line (`<a name="line">`), which is an HTML block the
    rule does not read. A fix would give the converted token's id or name an element to land on, a second reading of a
    tag
    the rule made text; the user decides whether it is worth one, as for the slug
    (`tools/file-review-plan-inlinetag-records.test.mjs` holds this clause, and runs the rule over both spellings
    where marked is installed). Two consequences the build found and kept: inside an inline `<svg>` or
    `<math>` the rule applies by name, so a child written without its own end tag (`<svg><title>icon</svg>`,
    `<svg><foreignObject><b>x</svg>`,
    `<math><annotation-xml encoding="text/html"><b>x</math>`) is text too and the root's own end tag closes the root
    (in the DOM those characters are svg text, present in the textContent the map and the reader match and drawn
    nowhere, or go with a dropped `<math>`; the alternative, `</svg>` and `</math>` closing every tag opened after
    their root as the HTML parser does, would have kept `<svg><title>icon</svg>` an element, and was not taken); and
    a class of shapes moved into the breakout class anchor-map-html-text-browser.test.ts already recorded, widened
    from the one shape first recorded there (`ma6 <math><annotation-xml encoding="text/html"><b>x</b></math> y6`) by
    the review of the slice's PR (round 1, 2026-09-19) and bounded again by its closing check (2026-09-19): an
    integration point of an INLINE `<math>` left open (`<mtext>`, `<mi>`, `<mo>`, `<mn>` or `<ms>`, or an
    `<annotation-xml>` with the html or the xhtml encoding) is literal text now, so an HTML element after it whose
    start tag is on the parser's foreign-content breakout list (the 44 names the HTML standard lists there, and `font`
    when it carries `color`, `face` or `size`) stands in the math's foreign content with no integration point around
    it: the parser breaks out of the math at it, whether the tag is closed, self-closed or void, and shows its text,
    and the reader drops the math whole. In Chromium `ma7 <math><mtext><b>x</b></math> y7` shows `ma7 x y7` where the
    reader reads `ma7 y7`, the same for `<mi>`, `<mo>`, `<mn>`, `<ms>` and the xhtml encoding in place of the
    `<mtext>` and for a closed `<div>` or `<p>` in place of the `<b>`, and `ma5 <math><mtext><p>a<p>b</p></math> y5`
    shows `ma5 b y5` against `ma5 y5`, no paint mark on either; before this decision both sides read `ma7 y7` and `ma5
    y5`. The `font` bound the same way: `<font color="red">x</font>` after the `<mtext>` breaks out (`P[FONT]`, `x`
    shown) and `<font>x</font>` goes with the math. What the class changes for the map, executed in Chromium at this
    head and at the base tree c25a2b319 over a note of the tag's paragraph, a heading and two paragraphs (a paragraph
    holding an inline `<math>` with text inside it was refused with the mismatch sentence on both trees in every shape
    run, `Lead <math><mi>x</mi></math> tail t1.` among them, and one holding `<math></math>` mapped): the void
    members break out with no closing, `<br>` and `<img>` inside
    `<math><mtext>` landing in the paragraph as a line break and a picture (the top-level elements `P[BR] H2 P P` and
    `P[IMG] H2 P P` against the base tree's `P H2 P P`, the text the same on both sides), the tag's paragraph refused
    with the mismatch sentence where the base tree mapped it and every later block mapping; `<hr>` closes the
    paragraph as well (`P HR P H2 P P`), so the paragraph's tail stands in an extra top-level element and every later
    block is refused with `The selection could not be matched to the file text.`, where the base tree mapped every
    block, the same after `<mi>` or the xhtml `<annotation-xml>` in place of the `<mtext>`; the self-closed `<b/>`
    breaks out and opens, a wrapper around every later block (`P[B] B[H2,P,P]`, every passage refused with the
    mismatch sentence), where the base tree showed `Lead` alone with the rest of the note gone (the `b` the flag does
    not close stayed open inside the `<mtext>`, the round-7 shape that keeps `</math>` ignored). A closed block-level
    member splits the paragraph the same way in either root: `<div>x</div>` or `<p>x</p>` after the `<mtext>` (`P DIV
    P H2 P P`, `P P P H2 P P`, the `ma5` shape's) and inside an inline `<svg>` after a `<title>`, `<desc>` or
    `<foreignObject>` left open (`P[svg] DIV P H2 P P`, `P[svg] P P H2 P P`; `<hr>` after the `<title>` the same),
    every later block refused with the could-not-be-matched sentence, where at the base tree the element sat inside
    the integration point, a scope boundary the parser closes no `<p>` across, and every later block mapped. Inside
    the `<svg>` the TEXT agrees on both sides for a member, since the sanitizer keeps svg text: `sv1
    <svg><title><b>x</b></svg> y1` reads `sv1 <title>x y1` on both sides, the `b` broken out into the paragraph
    (`P[svg,B]`) and every block mapping; the map is what differs for a block-level member, and the browser suite
    compares text, so the splits are RECORDED there by the DOM's top-level tags and each passage's verdict, not by
    text alone. The `<title>` half of the svg split stands as prose, executed and not pinned:
    `tools/markdown-viewer-plan-decision52-pointers.test.mjs` refuses a `<textarea>`, `<plaintext>`, `<title>` or
    `<noscript>` written without the self-closing syntax in a RECORDED source, since such a tag left open is literal
    text under this decision and cannot itself be a recorded divergence, and the svg-title shape's divergence is the
    div's breakout, which the guard cannot tell from a title left open, so the split is pinned through
    `<foreignObject>` and `<desc>`. Not in the class: a closed element whose start tag is not on that list (`<kbd>`,
    `<a>`) stays in the
    foreign content and goes with the dropped math on both sides (`ma7 y7`); inside an inline `<svg>` it stays in the
    drawing, where the sanitizer keeps an svg name (`<a>`, its text shown and every block mapping) and removes any
    other with its text, which the reader keeps as the drawing's, so `Lead <svg><foreignObject><kbd>x</kbd></svg> tail
    t1.` reads `Lead <foreignObject> tail t1.` in the DOM against the reader's `Lead <foreignObject>x tail t1.` (the
    same after a `<title>`), a text divergence new with this decision, RECORDED in the same suite; and a `<math>`
    inside an html block, whose tags the rule does not read. The reader does not model the parser's breakout from
    foreign content (the Slice 5 build note of plans/markdown-viewer.md records it as not modelled and pre-existing),
    so the class is RECORDED in that suite, the text representatives `ma5` and `ma7` and the closing check's entries
    for the void members, the self-closed `<b/>`, the `font` member, the block-level splits in both roots and the svg
    out-of-class drop, and not modelled; `ui/webview/anchor-map-html-rules.test.ts` pins the reader's side of `ma5`.
    Two divergences the
    Slice 5 build note of
    plans/markdown-viewer.md recorded (item 4) are agreements now: an inline `<textarea>` left open, and an
    `<annotation-xml>` whose encoding value carries a blank with a `<b>` left open inside it; the `/>` forms keep
    the divergence, since the self-closing syntax stays HTML. The assessment counted other placeholder tags in the
    note, start tags with no end tag that the sanitizer dropped with nothing shown; they render as visible text
    now. mdBlock calls marked's lexer and parser directly, so a throw from them no longer carries the report-this
    sentence marked.parse appends to its message (`fellMessage`'s cut is a no-op for the viewer's own parse and
    stands). docs/guide.md says so in its paragraph on a file's own HTML; CONTEXT.md is unchanged, since no
    term was coined.
    Tests: `ui/webview/md-literal-tags.test.ts` (the rule at the token level over marked's lexer, the escape held
    equal to marked's own text token for the same characters, idempotence, and the source pins: both callers import
    and call the function, mdBlock's three steps in order, the map's call on the lex line, one void list,
    md-config.ts and the chat's modules untouched, the module importing marked's types alone);
    `ui/webview/anchor-map-literal-tags.test.ts` (the map over a DOM stand-in that models the quirks-mode table
    nesting, foster parenting, the RCDATA elements and the sanitizer's drops; two FAILS-BEFORE cases, red with the rule
    absent (literalizeUnclosedTags a no-op, or its call removed from viewerHtml) at the mismatch sentence for four
    passages and at the blocks lost after an unclosed `<title>`; the closed, void, self-closing, matching, heading, list
    item, cell, offsets and untouched-shape cases; the RECORDED self-closing spelling of a known name, `<div/>`,
    `<table/>` and `<title/>` over the stand-in, the bare spelling of each mapping; and the RECORDED `<hr>` inline, the
    one void tag whose start tag closes an open `<p>`, with `<br>` as the control);
    `ui/webview/anchor-map-literal-tags-browser.test.ts` (the real pane and panel in Chromium: one top-level element per
    block, every passage mapped through a real Selection, a comment on the literal `<table>` painted through the panel
    and a change through the painter, the Raw view's range equal; and the RECORDED self-closing spelling in the real
    pane, `<b/>`, `<div/>`, `<table/>`, `<title/>` and `<textarea/>` with `<x/>` as the control, each shape and verdict
    the same over the base tree). The suites whose pins the rule changed
    follow it: `ui/webview/anchor-map-html-rules.test.ts`, `ui/webview/anchor-map-html-text.test.ts` and
    `ui/webview/anchor-map-html-text-browser.test.ts` (the foreign-content shapes above, the breakout class RECORDED
    with its two text representatives and the closing check's entries by top-level tags and verdicts),
    `ui/webview/anchor-map-fallback-markup.test.ts` and `ui/webview/md-config-merged-paragraph.test.ts` (their
    mdBlock replicas render through the rule), and the source pins over mdBlock's parse in
    `ui/webview/file-view.test.ts`, `ui/webview/file-view-links.test.ts`, `ui/webview/render-sanitize.test.ts` and
    `ui/webview/anchor-map.test.ts`. `tools/file-review-plan-inlinetag.test.mjs` holds this record and decision 53
    to the module, both callers, the guide and the tree; `tools/file-review-plan-inlinetag-rawblock.test.mjs` runs
    marked over a document with an unclosed `<kbd>`, `<pre>`, `<code>` or `<script>` and holds the scope sentence
    above to the lexer: every later block unescaped, an end tag of any of the four names clearing it, `inLink` the
    same, where marked is installed (CI's shell job installs nothing, so those legs skipped there);
    `ui/webview/file-review-plan-inlinetag-rawblock.test.ts` (the second round) runs the same documents through both
    callers' lexes under the one configuration inside the extension job's `npm test`, so the scope sentence has an
    arbiter in CI, and the tools module holds that twin and its runner to the tree. The first round added three
    modules more, named here since the second round found them recorded nowhere:
    `ui/webview/md-literal-tags-tag-syntax.test.ts` (the self-closing flag read as the tokenizer reads it, with the
    FAILS-BEFORE case on `<a href=http://a.test/>`; the `image` alias left HTML, a FAILS-BEFORE case too; the stacks
    per name held against the one list as an oracle, and their linear time under forty thousand stray end tags);
    `tests/test_guide_files_own_html_foreign_tag.py` (the guide's qualification for a child tag left open inside an
    inline `svg` or `math`, each clause held to this record, the module's by-name match, the sanitizer's profile and
    the DOM tests); `tools/markdown-viewer-plan-decision52-pointers.test.mjs` (the Slice 5 build note's four in-place
    pointers at this decision, held to the sentence above and to the browser suite's shapes).
    `tools/guide-own-html-block-tag.test.mjs` (the second round) holds the guide's account of where the rule stops, a
    tag first on its line that markdown lexes as a block `html` token, to the installed marked, to the rule's walk
    and to the map's refusal of an html block; since the review of the slice's PR (round 1, 2026-09-19) it holds the
    guide's sentence on the tags that take the rest of the file when they stay HTML too, `<title>`, `<script>`,
    `<style>` and `<iframe>` first on their line (block `html` tokens) or written with the slash mid-sentence (inline
    `html` tokens the rule leaves), `<textarea>` beside them. Its lexer legs skip where marked is not installed, which
    is every run of CI's shell job, so `ui/webview/guide-own-html-block-tag.test.ts` (the same round) runs them
    through both callers' lexes under the viewer's configuration inside the extension job's `npm test`, and
    `tests/test_guide_files_own_html_foreign_tag.py` holds that sentence in its place in the paragraph and the rule's
    two exclusions at the source. `tools/file-review-plan-inlinetag-records.test.mjs` (the second
    round) holds this record's account of the first round to the code: the stacks per name, `IMG_ALIAS` outside the
    void set, `isSelfClosingTag` and the two tags named above run through the installed marked and the rule, the
    `open` array's occupants and the self-closing spelling that still opens a wrapper, the fragment target a converted
    tag loses, the math breakout class and the loss before the rule after each raw-text name (the PR review's round
    1); and holds the Tests bullet's inventory both ways, every test module under
    `tools/`, `ui/webview/` or `tests/` that cites decision 52 or 53 named in the bullet or in one of the two
    records, so a later round's module cannot land unrecorded again.
53. **A selection across several cells of one table anchors to its span** (2026-09-18). Slice 8 of
    plans/markdown-viewer.md (item 3, the brief's open question 3) refused a Rendered selection whose source span
    covered two or more cells of one table with the sentence "This selection spans more than one cell of a table;
    select within one cell, or comment on it from the Raw view." and the Raw view offered on the covered cells'
    span, where Save worked, on the ruling that a quote across cells would carry the pipes between them and the
    rows' line feeds, raw delimiters the person did not select as text (the Slice 5 ruling that declined raw HTML in
    a quote for the wrappers). The assessment of 2026-09-18 listed anchoring such a selection as a low-risk change
    whose span the refusal already computed for its Raw offer, and the user overturned the ruling: the selection
    anchors instead of refusing, the raw delimiters inside the quote accepted.
    The rule: `mapRenderedSelection` maps such a selection as it maps any selection over more than one block. The
    anchor runs from the selection's first positioned character to its last, both from the pass as before, widened
    by a formula the selection covered whole at either end (the existing `widened`, over the formulas
    `formulaBeside` and the InControl boundaries found), so every cell the span covers lies inside it, a
    formula-only or picture-only cell the span runs through among them, and the quote is the source between, the
    pipes, the delimiter row and the line feeds included, the characters a Raw selection over the same text mints
    (each anchor in the suites is held equal to `mapRawSelection`'s over the same offsets). Nothing was added to the
    algorithm: the anchor is the line that already followed the refusal, `widened` over the first and last
    positioned characters and `source.slice(start, end)`. The one-cell machinery is gone from the map: the constant
    `ONE_CELL`, `cellsRule` (the count of a table's cells by source span and its refusal), `coveredCells` (the same
    over a covered formula's table), `coveredOnly` (the covered formulas' span handed to that count), the pass's
    per-table check and the final covered-cells check before the ok return. The Cell records `walkRow` keeps stay,
    read by `renderedSpot` to place a change's point inside one cell's own characters. The Raw offer stands for the
    refusals that remain: the pass still names a refused visible block and a hole's characters in document order and
    `formulaEnd` after them, so a selection that leaves a table into an html block, a code block the reading could
    not place, a callout's title or a formula keeps those refusals, the cells it crosses no obstacle now (the
    re-aimed pins name the next obstacle in the span). Two edges are the build's reading of the contract, which said
    to keep whatever the formula rules still need, and not a ruling: a selection whose characters are covered
    formulas alone, two formula-only cells with nothing positioned between (the shape `coveredOnly` served), is the
    formula's (`FORMULA_TOUCHED`, the Raw view offered on the formula the drag began on, as a paragraph's selection
    of formulas alone is), not an anchor to `$x$ | $y$`; and a picture alone in a cell is no formula, so a drag
    released on the cell pad past a picture-only cell anchors the positioned cells alone (`covered` is filled by the
    formula detections, and no picture-beside detection was built), while a picture-only cell the span runs THROUGH
    lies inside the quote. The user's word on either is open (Open questions).
    The paint rule: the rendered paint of a multi-cell anchor needs no new rule. `paintRendered`'s exact path finds
    the first and last positioned characters whose source offsets lie in the range across blocks, `wrapBetween`
    reads the highlight units under both ends' block nodes and the covered formulas, and `wrapRuns` wraps one mark
    per run of adjacent siblings, skipping the whitespace-only text nodes between block boxes (TD, TH, TR and P are
    BLOCK_BOXES), so every covered cell gets a mark over its own text and the pipes get none; a tracked-change mark
    over the same span paints the same cells. Verified in node by extracted strings and in Chromium: the saved row
    comment's marks read `cell one` in the first cell and `cell two` in the second, none over the pipe, and the Raw
    view paints `cell one | cell two` on the row; a comment saved over a paragraph and an all-formula header row
    paints in the paragraph and in both header cells, each cell's mark holding its KaTeX formula. The composer folds
    a quote's whitespace to blanks (`.fc-quote`), so a quote across rows shows as one line, `Intro para. | $h$ |
    $k$` for the stored `Intro para.\n\n| $h$ | $k$`, while the stored quote keeps its line feeds (verified from the
    posted write in Chromium): fine for a one-row quote; a multi-row quote reads with blanks where the file has line
    breaks.
    Records: docs/guide.md's Comments paragraph says a table cell, a selection across several cells of a table and a
    line of a code block can be commented from the Rendered view like any passage, that a comment across cells
    quotes the pipes between them as the file holds them, and names a formula as what cannot be mapped (the
    refusal's tail clause the other pins read is byte for byte as it was); anchor-map.ts's header, the Cell
    docstring, `walkRow`'s, `widened`'s, `orFormula`'s note, the obstacle-order note and the anchor site state the
    rule and keep the one-cell rule as history; plans/markdown-viewer.md's Slice 8 record keeps its account of the
    one-cell rule as the slice built it, with one sentence at item 3 pointing here. Tests:
    `ui/webview/anchor-map-cells.test.ts` (the shapes Slice 8 refused: two body cells, across two rows, a header
    cell into a body cell, prose before into a cell, a cell into prose after, the whole table, one character into
    the next cell, two tables through the prose between, each held to an exact quote and range and equal to the Raw
    path over the same characters; a FAILS-BEFORE case on two body cells, `ONE_CELL` before, the anchor with the
    pipe inside the quote after; the paint across cells and a change over the same span);
    `ui/webview/anchor-map-cells-formulas.test.ts` (the Slice 8 review's round 4 and 5 shapes, anchors now: a
    formula-only cell at the start, at the end or run through inside the quote, a picture-only cell run through, the
    pad past a picture, two formula-only cells alone the formula's); `ui/webview/anchor-map-cells-browser.test.ts`
    (a real drag across two cells saved through the panel, one mark in each cell and none over the pipe, the Raw
    view's mark across the row; the all-formula header row saved with marks in the paragraph and both header cells;
    the edge cells' composer quoting the cells and the prose after); the pins re-aimed at the next obstacle in
    `ui/webview/anchor-map-obsidian.test.ts`, `ui/webview/anchor-map-code-lines.test.ts` and
    `ui/webview/anchor-map-wrappers.test.ts`; `tests/test_guide_files_cells_and_code_lines.py` (the guide's
    sentences flattened and, at the source, the header's sentence, the absence of `ONE_CELL`, `cellsRule`,
    `coveredCells` and `coveredOnly` and of the one-cell sentence, and the anchor and return lines);
    `tools/file-review-plan-inlinetag.test.mjs` holds this record to the source and the guide.

## Open questions for the user

Every question raised by this document, by its reviews, or in the design interview has been ruled
on; see Decisions. The tie-break's first rule as the review's third round qualified it (decision 51: the
ordinal's copy is confirmed unless the stored heading path names other copies and not the ordinal's, when
the tie is a guess) departs from the contract the user said yes to, which confirmed the ordinal's copy
whenever the count of copies was unchanged; it awaits the user's word, and the code and the record hold
the qualified rule meanwhile. The margin layout (the follow-on note under Slice 2) awaits the user's word: it
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
Two edges of decision 53 (2026-09-18) are the build's reading of its contract, not a ruling: a selection
whose characters are two formula-only cells of a table with nothing positioned between is refused as a
formula, with the Raw view on the formula the drag began on, rather than anchored to the cells' span; and
a drag released on the cell pad past a picture-only cell anchors the positioned cells alone, since a
picture is never covered as a formula is. Both stand until the user says otherwise.

## Upstream

The user intends to offer the whole feature upstream to romp eventually (the user 2026-09-05).
Vendoring the core and the agent-side tooling (decisions 4 and 15) makes the loop
self-contained, so the whole feature can be offered as one; Slice 0 is also a candidate row on
its own. The offer decisions belong to the offer flow, not this plan.

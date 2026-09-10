# Guide

This guide covers how to use Romp and how its back end works.

## The Romp user interface

Romp gathers all your Claude Code sessions into one interface, with six
complementary panes:

- **[The chat](#the-chat)** is the regular interface for talking to a coding
  agent, with features that make a long session easier to scan.
- **[The feed](#the-feed)** is Romp's task-management layer: what is in
  progress, what needs your input, and what is done.
- **[The timeline](#the-timeline)** is the history of what each session worked
  on and how they coordinated; click any part to jump to that moment in the
  chat.
- **[The outline](#the-outline)** lists every session with its tasks, for
  reviewing what a session has done and searching across all of them.
- **[Waiting on you](#waiting-on-you)** lists every user todo a session has
  flagged for you, across all your sessions and machines, with Reply and
  Dismiss on each.
- **[Files](#files)** holds the file viewer in a column of its own, so a file
  stays open beside the chat and the feed.

### The chat

![Tool calls fold into runs; each expands to one line per call](assets/guide/chat-detail.png){ width="100%" }

**Commenting on a file.** Select any passage in the file viewer and it lands in the
composer as a quote chip, labeled with the file and the line the passage lives on. Type
what should change and press **⌘⏎** to set the note aside; keep reading, select the next
passage, and repeat — each staged note remembers its quote and its place. The list above
the box shows about four staged notes and scrolls for the rest; its caret folds it to the
count. **⏎** sends everything you staged along with whatever is in the box as one message,
so the session applies the lot in one pass, and you never copy a line out of the document
by hand. The line in each
label is checked against the file at the moment you select, so numbers that moved under
you are caught rather than quietly carried. Chips are one-off notes: they go out with the
message and are not kept. For anything worth keeping with the file, use the viewer's
**Comments** panel, described under Files: a file comment is stored beside the file, the
session replies into it, and its edits to a tracked file come back as changes for you to
accept or reject. When several sessions work in the same
repository, or in worktrees of it, the viewer's title bar says which one you opened the
file from: a chip with the session's name, in the same color as its tab. The title bar's
**GitHub ↗** button opens the file on GitHub. While the check runs, the button waits dimmed
with pulsing dots beside it.
When there is nothing to open, the button stays in place, dimmed, and a caption beside it
says why (the file is not in a git repository or not committed — untracked, staged but in no
commit, or on a branch with no commits yet — the repository has no origin remote, its origin
is not on GitHub, or the path is relative and no session's directory resolves it); the
button's tooltip repeats the reason. A file on a branch that is not on origin keeps its link,
drawn with a dashed border, and the caption says the branch is not on origin yet. That check
trusts your clone's own refs: a branch deleted on GitHub reads as present until `git fetch
--prune`, and one pushed from another clone reads as absent until a fetch. A branch that has
never been pushed is asked of origin once and the answer kept until a push or fetch from this
clone writes its tracking ref; where nothing local could refresh the answer (a
`--single-branch` clone, or a branch on origin this clone has not fetched) origin is asked on
each open.
A pull request number in a message, a card, or a note (`#123`, `PR #123`, or
`owner/repo#123`) links to that pull request on GitHub, in the repository the session's
directory has as its `origin` remote; when that remote is not on GitHub, the number stays
plain text.

**Pinned notes.** A session can pin a short note for you above its transcript: where things
stand, a warning, a summary. The notes appear in a strip between the tab bar and the transcript,
oldest first, one line each, and the strip is absent while a session has pinned nothing. Click a
row that shows a *details* hint to read the rest (a cut line's full text is there too); when more
than three notes are pinned, the older ones fold behind a *+N more* row, and the strip scrolls once
it is a few rows tall. Paths and pull request numbers in a note are links. **Unpin**, clicked
twice, removes a note; a session can also unpin its own. A note stays until unpinned, across
restarts and revivals, and a session keeps at most eight; a ninth drops the oldest.

**Opening a markdown document.** A markdown link in the chat opens in the file viewer,
rendered, with **Raw** one click away — a path on the session's machine, or a link to a
file served from the dashboard's own address (a published report, an evidence doc). Figures
and links inside the document resolve relative to the document, so a `![fig](fig.png)`
beside it shows, and a link to a sibling document opens in the same viewer. Links to files
on other sites open in a new tab, as before — and a ctrl- or ⌘-click still opens the file in
a tab.

**Opening a PDF.** A PDF the session mentions, or one you click in the file browser, opens
inside the dashboard like an image: the chat's PDF card opens it full-view, a path or a
file-browser row opens it in the file viewer. Cmd-click it instead (Ctrl on Windows and
Linux), or middle-click, and it opens in a new browser tab in the browser's own viewer, the
way a paper opens from OpenReview: full size, and it stays open beside the dashboard while
you keep working. If the browser blocks that new tab, the PDF opens inside the dashboard
instead; a PDF too large to show offers a download in its place. Commenting on a PDF, and
what the viewer does while the **Comments** panel is open, is described under Files.

**Naming another session.** Type `@` and the first letters of a session's name in the
message box, and the sessions whose names match are listed above it, twelve at most; when
more match, the last row says how many, and more letters narrow the list. Arrow to one and
press **⏎** or **Tab**, or click it, and `@name` goes into the message as plain text, the
name the session's mail tools take. Which form goes in depends on the session you are
writing to. Writing to a session on this machine, a session on another machine is inserted
as `@host:name`, the way this machine knows it. Writing to a session on another machine,
every name is inserted bare, because the dashboard cannot see what that machine calls its
peers; if the bare name is ambiguous there, the session's mail tools refuse the send and
list the candidates as `host:name`, and the session picks one. **Escape** closes the list
without inserting, and it stays closed for that `@` until you delete it: more letters, or a
caret move away and back, do not reopen it. In the sent message, a name that matches a live
session is shown as a chip in that session's color.

**Sending while the session is working.** The session takes your message at its next
step. In an SDK session the message stays where you sent it: it sits below everything that
had already happened, the steps the session runs in the meantime appear below it, and when
the session takes it, it lands in that same place. Send several messages during one turn (a
composer message, then a todo reply) and each reaches the session as its own message, in
the order you sent them: the next one waits, shown as queued, until the session has taken
the one before it, so two messages are never joined into one. A tmux session takes a
message only while it is idle, so messages sent during its turn wait, shown as queued, and
arrive together when the turn ends, as one message.

**While a message is on its way.** A message you have sent shows as a dashed bubble
marked "sending…" until the session records it, however long that takes; the bubble
never gives up on its own. If the connection drops before romp has confirmed it received
the message, the bubble reads "not confirmed"; it returns to "sending…" once romp
confirms, and clears when the message lands. ✕ puts the text back in the composer to
send again. Each bubble reports its own state, so one dropped message and one still on
its way read "not confirmed · sending…", and ✕ acts on the bubble you press it on.
Sending the same text twice shows two bubbles; romp confirms them one at a time, as it
receives each copy, and each clears when its own copy lands.

**Tags and groups.** A tag is a named, colored set of sessions; a session can be in
several. Right-click a tab and open **Tags** to add or remove them. Tags filter every
surface (the tag button in the strip narrows the tabs to the tags you pick), and they group
the tabs: as soon as any session carries a tag, the strip shows one section per tag, in your
tag order, each with a header in the tag's color, and the untagged sessions after a divider
at the end. A session with several tags appears under each of them; every copy is the same
session (click either to open it, and closing either ends it). Each header shows a chevron, the tag's color, its name, and a
member count. Click a header, or press Enter on it, to fold its section down to the header
alone; the count then says how many tabs are folded away, and a small dot after it says when
one of them is working or waiting on you (hover it for their names). A folded header keeps the ⚑ flag
of any session in it that has asked you for something; when several have, the flag shows how
many, and hovering it names them. Click the flag to open the section. To keep one tab visible
while its section is folded, right-click the tab and pick **Show when folded** under **Tags**;
the header's count and flag then leave that tab out; when every tab in a section is set to
show, the folded header shows the full count and its tooltip says nothing is hidden. Pick it
again to fold the tab with the rest. A tab set to show when folded keeps that setting when its
group is renamed. The `archived` section starts folded. Drag a header to reorder the groups, which
reorders the tags on every surface (the timeline's tag table shows the same order). To move
a tab into another group, right-click it and pick **Move to <tag>** under **Tags**: one click
adds that tag and drops the tag of the group you right-clicked it in, leaving its other tags alone. The row's
**+** adds the tag without moving the tab. **Group tabs by tag**, at the foot of the tag
button's menu, turns the sections off for this browser. The groups follow one another across the
strip and wrap as they need (a header left at a row's end with its first tab on the next row moves
down to join it, when the two fit on one row); the gear's **One tag group per row in the tab strip**
starts every group on its own row instead.

**A section at a glance.** Clicking a header also shows the section in the transcript's place:
one row per session, with its color and emoji, a dot for its state (yellow working, red stopped on a
prompt or an API error only you can clear, amber retrying an API error on its own, teal compacting,
green waiting on background work, none while it is idle), a **needs you** or **waiting** word, a ⚑
when it has asked you for something, what it is doing now in a few words, and how long ago it last
did anything.
**Needs you** appears when the feed shows one of the session's cards under Blocked, when the
session is stopped on a prompt or an API error only you can clear, or when it has flagged a todo
for you; **waiting**, when it is waiting on background work. A session that asked a question and
went quiet shows the word with no dot: the dot follows the session's own state, the word follows
the feed. What it is doing now comes from its current task, else from the headline of
its work so far, else from the last task it had; a session that has published a note of what it is
working on shows the note as a quieter second line. Hover a row for its last message, shown without
its formatting; click one to open that session, which also opens its section if the section is
folded (with several tags, the first folded group of them that does not hide it; a section that
hides the session stays as it was; see the next paragraph). The rows update as
the sessions work and change only when something about a session changes; the **needs you** word
follows the feed, at most a moment behind it. The section of the tab you are reading folds like
any other; its header then stands in for the tab (the name is underlined, ←/→ step from there).
The transcript comes back when you pick a session, press Escape, or click that header again while
its section is open and holds the tab you are reading. Sections, and this view with them, are for
the desktop layout; the phone layout keeps its flat list.

**Hiding a session inside its group.** Each row in this view has a **Hide** button, or **Show**
once the session is hidden. Hiding a session takes its tab off the strip while its group is open
and moves its row under a **Hidden (N)** fold at the foot of the view, one click away; the row's
**Show** button puts the tab back at once. Hiding is separate from folding: fold the group and
open it again, and the hidden sessions stay hidden while the rest come back. Nothing is lost by
hiding. The group's header keeps the dot and the ⚑ flag for its hidden sessions (the dot is red
when one of them needs you), and its count shows two numbers, **6+2** for six on the strip and two
hidden (the tooltip spells it out). When a hidden session needs you, the fold's head says so in
red before you open it, and its row says **needs you**. While the
group is open, its count opens this view without folding the group, so hiding a session never needs
a fold; the dot and the flag, which appear once something is hidden, do the same. On a folded header
the flag opens the group, as before. While this view shows an open group, its count, dot and flag take
you back to the transcript. Clicking a hidden session's row shows its transcript, with the header
standing in for the tab, and leaves it hidden, its group folded or open as it was, unless the
session has another tag whose group is folded and does not hide it: that group opens and the tab
shows there, the hide standing where it was. A session set to **Show when folded** stays hidden
while it is hidden: the hide wins, and the setting resumes when you show it again. A hidden
session keeps the setting when its group is renamed, and shows again wherever it lands when it
leaves the group. Like the sections, hiding is per browser and for the desktop layout.

**On a small screen.** To keep more of the transcript in view, turn on the gear's
**Compact tabs and agents** setting. It tightens the rows in the box of background work above the
message box (the one headed **Awaiting** or **In the background**) and caps that box's list at
about four rows that scroll; the cap lifts while a row's details are open. Where the tab strip is
showing (a desktop-width screen, or a tablet wide enough for it) it also shrinks the tabs and group
headers; on a phone the session picker stands in for the strip, so there the setting tightens the
box. Like the other chat settings, it is per browser.

### The feed

The feed is Romp's task-management layer: a card for each task. Romp's
[judges](judges.md) watch each session's work, split it into those tasks, and
keep every card current.

Cards sit in three columns:

- <span class="romp-chip romp-chip-working">Working</span> — the session is
  actively working on the task.
- <span class="romp-chip romp-chip-blocked">Blocked</span> — it needs your
  input to move on.
- <span class="romp-chip romp-chip-completed">Completed</span> — done, ready
  for you to review and clear.

![The feed's three columns, with the cues on a card](assets/guide/feed-annotated.png){ width="100%" }

<span class="romp-btn">Background</span> is why the agent is taking the action,
and <span class="romp-btn">Summary</span> is what it did. When a task divides
naturally into parts, the card's <span class="romp-btn">Sub-goals</span> button
opens them.

Cards follow the work rather than the session: one session can hold several
tasks, and a task can be handed from one session to another.

Press <span class="romp-btn">Clear</span> on a card when you are done with it. A
cleared card is archived, and no more work is added to it.

### The timeline

Each row is one session. A bar is a stretch where the session was working, and a
circle is a message you sent. A striped stretch means the session is blocked,
waiting on your input.

![A timeline lane per session, with status and context at the left](assets/guide/timeline-annotated.png){ width="100%" }

Click a bar or a message marker to jump straight to where it happened in the
chat.

Session statuses:

![Each session state and what its color means](assets/guide/status-legend.png){ width="70%" }

### The outline

Every session with its task tree: open work stays up top, finished work folds
beneath. Open the outline to review what a session has worked through, or to
find past work: the search box reaches every session, live or closed.

![The outline: each session's tasks as a tree](assets/guide/outline.png){ width="100%" }

### Waiting on you

One list of every user todo a session has flagged for you, oldest first,
across every session and every attached machine: a decision it needs, a
credential, a pick between two designs. Each row names its session and shows
how long the todo has waited. Reply sends your answer straight into that
session, waking it if it has gone quiet; Dismiss clears the todo without a
reply. A file path in a todo's text or its detail is a link: click it and the
file opens in the Files pane, which comes forward if it was closed. Absolute
paths, `~/`, `./` and `../` paths and `file://` URIs link as they are; any other
relative path links only when its last segment has a file extension
(`notes/plan.md`, not `notes/plan`). A todo that names its file also shows the
file's name as a chip on the row and in the Reply box, with the full path on
hover; the session's own todo card in the chat shows the same chip. Click the
chip and the file opens the same way; a **Send to session** from that file can
then answer the todo (see Files). A web address in a todo's text or detail is a
link that opens in a new tab, and a todo that carries its own address shows it
as a second chip beside the file's, the whole address on hover. The pane is off by default, like the outline;
turn it on from the bottom bar. Sessions flag todos only where
the gear's **User todos** switch is on, and the switch is per machine: while it
is off on this one, the pane says so and still lists the
other machines' todos. A todo you expected can be missing for two reasons. A
session that has ended keeps its todos out of the list until you revive it
(click **+**; closed sessions are listed under **Recent**). A session you have
hidden from the feed (right-click its tab, **Hide from feed**) keeps them out
too, though its tab still shows the ⚑ mark; **Show in feed** on the same menu
brings them back. The file the todo named is still on disk.

### Files

The Files pane holds the file viewer in a column of its own, beside the chat
and the feed, so an open file covers neither. While the pane is open, a file
link clicked in the chat opens here. When it is closed, the gear's **File
links open in** setting decides where a link opens; set it to **The Files
pane** and the pane comes forward on its own and stays up until you close the
file. The folder under the chat (the session's working directory) opens a
listing of that folder by the same rule: in this pane while it is open or when
the setting names it, otherwise over the feed. Pick a file in the listing and
it opens where the listing is. Selecting
a passage in it puts the quote in the chat's composer, as it does from the
viewer over the chat. When no file is open, the pane lists the files most
recently open here; click one to open it again. The pane is off by default;
the bottom bar turns it on.

**Links in a file.** Wherever the viewer shows a file's text, over the chat, over
the feed, or in this pane, the links in that text work. A web address opens in a
new browser tab. A file path opens that file in the viewer, in place of the one
you were reading: a relative path such as `docs/guide.md` is taken from the
folder of the file you are reading, an absolute or `~/` path as written, on the
machine of the session the file belongs to, and a line written after the path
(`src/app.py:12`, or `src/app.py#L12`) scrolls the Raw view to that line. A
Markdown file opens in its Raw view for that one open, since the Rendered view
has no lines; your Raw/Rendered choice is unchanged. A line past the end of the
file lands on the last line, with a notice saying so. In a Markdown file, a
`[link](target)` follows the same two rules: a web target opens a tab, a file
target opens the file (a host with a port, `127.0.0.1:3000` or
`api.example.com:8443`, is neither, and says so). A link to a section of
another file (`report.md#results`) opens that file at the section. A link to a
section of the same document scrolls to it
when the document has a heading or an anchor by that name (`<a name="install">`
included), and otherwise says so when you hover it; it scrolls under every
click, since a section of the shown file has no tab of its own. One click does
one thing: a plain click acts in the dashboard, and a Cmd-click (Ctrl on Windows
and Linux) or a middle-click opens the link in a browser tab of its own. Where a comment highlight or a change mark covers a
link, a plain click opens the comment or the change and leaves the link alone.
Inside a file the test for a path is stricter than the one a todo or a chat
message gets: a path links only when it has a slash and a file extension, starts
on its own, at the start of a line or after a space, a quote, a bracket or
Markdown's `*` (so `$HOME/docs/a.md`, `@scope/pkg/index.js` and
`C:/Users/x.txt` stay text), is not part of a web address, does not start with a site name
(`www.example.org/docs/index.html`), and is not the package an `import`
statement or a `require()` call names, whether the statement fits one line or
its `from` starts the next (a relative import such as `./app.css` still links,
and so does a path after the English word "from" in prose, unless that line
holds nothing but `from` and the quoted path). After a `*` the path must be
the whole emphasised text, closed by a `*` of its own: `*docs/a.md*` and
`**./scripts/setup.sh**` link; a glob's `**/docs/a.md`, an operand's
`w*h/img.size` and the first path in `**docs/a.md and docs/b.md**` stay text. Web
addresses and paths found in the text wear a dotted underline that
turns solid under the pointer; a Markdown link that names a file keeps the
ordinary link look. Selecting text across a link, and commenting on a line that
holds one, work as before, and a drag that starts or ends on a link selects
rather than opens.

**Text size and width.** The **A−** and **A+** buttons in the viewer's title bar make
the text of any text file smaller or larger in fixed steps from 70% to 200%: a markdown
file's Rendered and Raw views, and the code view of every other text file. They appear
on every surface that shows the viewer (over the chat, over the feed, in this pane), and
not for a picture or a PDF, which have no text to size. Ctrl (or Cmd) and the mouse
wheel over the text do the same. Once the size is off 100%, the percentage appears
between the buttons; click it to go back. The choice is kept in this browser and applies
to every file you open here. The prose of a rendered markdown file is a column of about
eighty characters, centred in the pane. A step up in text size widens the column to keep
its eighty characters while the pane has room for them; in a pane too narrow for that, the
column fills the pane, leaving a small gutter on each side, and each step up fits fewer
characters on a line. Code blocks keep the column and wrap long lines. A table no wider
than the column sits with the prose. A wider one grows out of the column evenly, up to the
width of the pane, and scrolls inside its own box beyond that; a table inside a quote or a
list item stays within the prose width. Pictures shrink to fit, so resizing the pane never
leaves the page wider than the pane, and a picture sized in pixels by its `width` and
`height` attributes keeps its shape as it shrinks; one whose width is a percentage keeps
the height it names.

**How a markdown file reads.** The Rendered view shows a markdown file the way GitHub
shows a README. The text is a little larger than the dashboard's own (15 pixels where the
chat is 13), in the same sans face in both themes. Headings step down from twice the text
size for a top-level heading to the text size for the fourth level and below, with a rule
under the first two levels; the fifth and sixth levels are dimmed. A task list shows its
boxes without bullets, ticked where the file says so. A table's header row is bold on a
faint fill, every second row is tinted, and a column the file aligns with `:---:` or
`---:` is centred or right-aligned. A `<kbd>` key reads as a key. Every fenced code block
is numbered by line, wraps long lines and carries a **Copy** button that copies the
block's text; a block that names its language is coloured when the language is one the
viewer knows: bash, python, javascript, typescript, json, xml and html, css, markdown,
diff, yaml, rust, go, c, java, sql and toml (an ini file's grammar). A block that names
any other language stays plain rather than being guessed at. Comments in coloured code are
readable against the block. Printing the page while a markdown file is open prints the
file alone, black on white, across as many pages as it needs, without the title bar, the
Comments panel or the Copy buttons.

**Your place in the file.** The passage at the top of the view stays where it is when
the file is read again after a session writes it, when you switch between Rendered and
Raw, when the pane is resized or the Comments panel opens or closes, and when the text
size changes. When the viewer cannot tell which passage is at the top, as with an HTML
block that wraps the markdown after it, it leaves the view where the browser puts it, and
the passage at the top might change. A notice from the viewer (a line past the end of the
file, an edit the viewer refuses) sits above the file's text, wherever you have scrolled
to, and stays through a switch of view and a reload until the next notice replaces it or
you open the editor. A notice raised while you edit (a save that failed) goes when you
leave the editor; a warning about the comments log stays when the save that raised it
closes the editor.

**A file's own HTML.** The Rendered view keeps the HTML a markdown file carries, under the
rules GitHub applies to a README, so nothing in a file can move, hide or cover the viewer's
own controls. A `<style>` block is dropped whole. A form, its controls and a `<dialog>` are
dropped but their text stays as prose. A task-list checkbox stays but cannot be ticked. An
inline `style` keeps only its `color` and `background-color`, and only when the value is a
color name, a hex code, or `rgb()`, `rgba()`, `hsl()` or `hsla()`. A span colored that way
keeps its color; one colored with any other function, such as `oklch()` or `var()`, loses it.
A `background=` attribute is dropped, since it would load a remote image the moment the file
opens. An inline `svg`, a `canvas` or a `video` shrinks to the column, as a picture does. An
element's `id` or `name` is prefixed `user-content-`, as on GitHub; the viewer's own
heading ids are not, so a link to a heading in the file still lands on it, and a link to an
element's own `id` or `<a name>` lands on it under the prefix. A link in the file is handled
by its target, not by the element that carries it, a link drawn inside an inline SVG
included: a web address opens a tab, a file target opens the file in the viewer, and a
section link scrolls to it. An image map (`<map>`, `usemap`) is dropped, as on GitHub.

**Comments and tracked changes.** The viewer's **Comments** action opens a panel beside
the file, where each card sits level with the passage it is about and scrolls with the text;
when the column is narrow the panel drops below the file and lists the cards instead. The card
you click sits level with its passage whatever stands above it, and a long card folds to a few
lines with **Show more** at its foot. Neither happens in the list under a narrow column, where a
long card shows whole. Select a
passage in either view, Rendered or Raw, and press the **Comment** button that appears next to the selection (it
hides when you scroll and appears again when you select); type the comment
(Enter adds a line) and save it with **Cmd+Enter** on a Mac, **Ctrl+Enter** elsewhere, or the
**Save** button; on a phone or a tablet the button is the way, and the line under the box says so.
Saving leaves the text where it is. When the new card lands out of view, a line at the foot of the panel, **Saved · the card is above** (or **below**), says where it went; click the line to bring the card into view, or leave it: it goes with your next scroll, click, tap, or key, except Tab or a modifier key pressed on its own, so you can reach it from the keyboard.
In the list under a narrow column, the line stands under the panel's header instead.
**Comment on this file** leaves a comment on the file as a whole, which every file takes. When a passage cannot be mapped from the
Rendered view (a table, a code block), the panel says so, keeps your comment, and offers the
Raw view with the passage selected. Comments are stored beside the file, in the
`.trackchanges/` folder at the root of its project (the nearest git repository, vault, or
folder that already holds one; a file with none gets the folder created beside it), in the
format the session's own tools read. A comment made here and a reply the session writes are
the same object, and the two other editors that read the format see them too. Each comment
is a card in the panel: click it to expand or resolve it, and **Reply** opens the reply box inside
the card, under the comment and its replies. The passage it
refers to is highlighted in the file, and a comment on text that occurs more than once stays
on the occurrence you chose. When the file has changed around that occurrence and the panel can
no longer tell which copy the comment meant, its highlight is dashed and the card carries a
**passage recurs** tag: the copy shown is a guess, and the card says so. When the session has
rewritten the passage, the card
says so, and **Reveal** finds the passage in the Raw view when the Rendered view cannot
show it.

**Figures.** On an image, whether it is a file of its own or a figure in a markdown page,
drag a rectangle to comment on that part of it. The rectangle stays on the picture with the
author's chip, and the card shows that part of the image. When the image's bytes change the
comment is shown as stale until you resolve it, or press **Re-place** and drag the rectangle
again where it belongs now; the comment keeps its words and its replies, and only the
rectangle changes. A figure embedded in a markdown file, such as `![](plot.png)`, is loaded
from the file's own folder, so a relative path shows in the Rendered view; a web address or a
`data:` image is left as written. A figure path that starts with `~/` is not expanded to your
home folder: it names a folder called `~` next to the file, as other markdown viewers read it,
while a link that starts with `~/` does open under your home folder. A comment on an embedded
figure is stored on its embed line,
with the rectangle: the session's tools and the other editors place it on that line, and this
viewer paints the rectangle on the picture. Drawing a rectangle needs a mouse or a trackpad;
on a phone, comment on the file as a whole instead.

**PDFs.** A PDF opens in the browser's own PDF viewer. While **Comments** is open, the viewer
draws the pages itself instead, one below the other, so a rectangle can be dragged on a page
the same way as on an image; the comment names its page, and its card shows that part of the
page once the page has been drawn. Pages are drawn as you scroll near them, so until then the
card shows a line naming the page, and clicking it scrolls the page in. A rectangle drawn on
one page can be placed again on another. Pages are drawn only up to 25 MB of PDF; above that,
or when the page renderer cannot be loaded or the file cannot be opened, the browser's viewer
stays with a line above it saying why, and a comment on the whole file still works. The
renderer ships without pdf.js's standard fonts and CMaps, and without its JPEG 2000, JBIG2, and
fax (CCITT) image decoders, so a PDF that does not embed its fonts may show some text in a
system font, and an image in one of those encodings is left blank, with a line at the top of
the page saying how many; the rest of the page still draws, and the browser's own viewer shows
the whole page.

**Track changes** records a session's edits to the file as changes for you to accept or
reject, instead of letting them land silently. Turn it on for the file or for its folder,
and turn it on for the folder a session will write into *before* it writes: only edits made
while tracking is on are recorded, and a folder can be tracked before its files exist.
Each change is a card in the panel, grouped by the paragraph it falls in, and is marked in
the file in both views: an insertion is tinted, a deletion is struck at its point, and a
substitution shows both, the struck old text before the tinted new text. **Show changes
inline**, beside Track changes, hides the marks and shows them again; with the marks hidden,
the file reads as it is and the cards alone show the changes. The setting is kept for every
file you open. Once a file has a comment or a change, **All**, **Comments**, and **Changes**
appear under those two toggles and choose what the panel lists; Comments and Changes show
their counts. **Comments** lists only the comments, including comments on changes, and hides
the change marks in the file; **Changes** lists only the changes, each with the comments made
on it, and hides the comment highlights and the rectangles on figures; **All** lists both. The
choice is kept like the marks setting and changes only what is shown: **Send to session**
still sends everything unsent. Every card names its kind, **Comment**, **Change**, or
**Region**, before the author's chip, and its left edge is colored by kind, the accent for a
comment and a muted tone for a change, so the two are told apart at a glance. **Accept** keeps the text as it is and drops the record. **Reject** puts the old
text back in the file. **Accept all** and **Reject all** decide every change at once; Reject
all asks you to confirm. A deletion's card offers **Reveal**, which opens the Raw view at the
deletion, since a point is easy to miss; a change the current view does not mark, because it
cannot or because the marks are hidden, offers it too. Reply on a change's card leaves a
comment on the change itself, and the session's answer comes back to that card. You can also
comment inside a change without replying to it: a click on a change mark or a comment highlight
opens its card, and a selection made by dragging inside one leaves a comment on those words. A session's
tools refuse to rewrite an image or a PDF as text, so a tracked folder may hold figures. A session
that tries to write a tracked file any other way, with its editing tools or a shell command such
as `cp`, `tee`, `sed -i` or a `>` redirection, is refused and pointed at its track-edit command,
so its edits still come to you as changes.

**Edit** works while changes are pending. The editor shows them inline, an insertion tinted
and a deletion struck, and typing around them moves them with the text. Click a change to
accept it; Alt-click (Cmd-click on a Mac, Ctrl-click elsewhere) rejects it; undo restores
either, so nothing is final until you save. On a phone or a tablet, a tap on a change places the
caret and decides nothing: Save or Cancel first, then accept or reject from the cards. **Save**
writes the file and the changes together.
A save that is refused, because the file or its changes moved on disk while you were editing,
keeps your text and offers **Reload file**, which asks before discarding it; while you edit,
the panel says when the file changed under you. The session's own track-edit keeps working
throughout. A file with CRLF line endings cannot be edited while changes are pending, because
the editor rewrites its line endings, which would move them; accept or reject them first.

**Send to session** hands everything unsent to the session that owns the file as one
message, in your words: the comments and replies you wrote since the last send, each with
what it refers to and the commands the session needs to answer it. The number on the button
is what will go, and the confirm lists it, with a box for anything you want to add in your own
words, which go first in the message; words alone send too. When a
todo under Waiting on you names this file, or you opened the file from a todo, a checkbox
answers that todo with the same send; when several todos name the file, a row of choices
picks the one to answer, or none. When tracking is off, another checkbox
turns it on first, so the session's revisions come back as changes. When changes are pending,
a third checkbox, **accept the pending changes you have seen**, accepts before the send the
pending changes you have looked at: the ones already there when you first opened the panel, and
any that arrived later whose card was in view when you scrolled, clicked, tapped, or pressed a
key. That way the session's later edits arrive as new changes instead of folding into an old one.
A change you have not seen stays pending, and the checkbox says how many do, or, when you have
seen none of them, that nothing is accepted until you look, and is then off. A change the session edits again after you looked at it counts as unseen until you look again. The message then
says how many changes you accepted and rejected. All are checked by default. One send
answers one todo; a todo that named several files is answered by the first, and later sends
no longer offer it. The panel then says **Sent to** the session and when, or **Queued for**
it when the session has gone quiet, in which case the message goes when it wakes.

While the panel is open it checks the file, its comments, and the project's tracking list
every few seconds, so a reply the session writes appears without a reload and a file the
session rewrote is shown as it is now.
A line under the panel's header counts the changes, comments, and replies the session added since you last looked, and each of their cards wears a dot until you scroll or click with it in view; click the line to open the first of them. The first comment, like the first save, asks once
whether the dashboard may write files on that machine; the same switch, **File editing** in
the gear, turns it off again, and while it is off a send is refused too (it writes the log)
and asks for the consent back. The **Log** at the foot of the panel is the comments log: what
was sent and when, the changes you accepted or rejected, tracking turned on or off, and your
direct edits to the file, kept beside the comments in the same folder so git keeps it when the
project does. Once a change is decided, its card is gone and the Log keeps the decision: the row
gives the count, and clicking it shows the old and new text of each change. Whether
`.trackchanges/` is committed is the project's call; a `.gitignore` line keeps it out. Sessions are
asked to include the folder when they commit their own work, so the comments and the changes are
kept with it; your commits are yours, and nothing here stages or commits anything.

If the **Comments** action is missing on a file, the gear's **File comments** row says why:
the kernel that owns the file has no node on its PATH, or it predates the feature. The same
row warns when sessions on that machine cannot reply because their tooling is not linked
into `~/.claude`; running romp's `install.sh` there links it.

## Automatic nudges

Agents stall: they hit an API error, they get interrupted, or they end a turn
leaving it ambiguous whether a task is done. Romp nudges a stalled session with
an injected message, so every task ends up either explicitly done or explicitly
needing your input.

Romp asks the agent, item by item, where each open piece stands: continue what
it can, and say what blocks the rest.

- If the agent can keep going, it does, and you were never interrupted.
- If something needs you, the card flips to <span class="romp-chip romp-chip-blocked">Blocked</span> and names exactly what
  it needs.

Nudging engages only when you are not actively messaging the session, so it
never talks over you and never loops on its own messages.

A session can also be waiting on something unrelated to you: it dispatches work
into the background, then pauses for the result. In that case it shows an
<span class="romp-chip romp-chip-await">Awaiting</span> chip. The chip clears on the
session's next turn, when the task finishes or blocks, when you clear the card,
or as soon as you reply.

## Inter-agent communication (the Romp Postal Service)

Sessions message each other through a mailbox Romp gives them, and every
exchange is visible to you. Each session gets mail tools: send a message to a
session by name, check the inbox, and see who is live. Each session also
publishes a working note saying what it currently holds, so agents can see who
to talk to instead of messaging each other to find out.

Not the same tools: romp peers are discovered only through the postal service's `list_agents`. Claude Code also ships its own `ListAgents` and `SendMessage` tools, which list the account's Anthropic cloud sessions and this session's own subagents: a different system, and a cloud session in that list is easy to mistake for a romp peer (the user 2026-09-08, who found one there that read like a session of theirs). The recommended setting is `"permissions": { "deny": ["ListAgents"] }` in the Claude Code settings, so the only list of agents a session sees is romp's; `SendMessage` must stay allowed, because continuing a subagent uses it.

The timeline draws an arc for each message. Hover one for its gist:

<video src="../assets/guide/coordination.mp4" controls loop muted playsinline preload="none" data-romp-autoplay width="100%"></video>

Underneath, a local message bus writes the message into a mailbox on disk that
belongs to the recipient, then delivers it: straight away if that session is
idle, otherwise when its current turn ends. The recipient reads it as a message
in its chat, and it appears in the user interface as a card naming the sender
and the kind:

![A message from another session, as the recipient's chat shows it](assets/guide/postal-chat.png){ width="100%" }

Every message declares its kind, which the card wears as a chip:

- <span class="romp-chip-kind romp-chip-delegate">delegation</span> — the recipient owns the work now.
- <span class="romp-chip-kind romp-chip-coordinate">coordination</span> — a heads-up; a reply is optional.
- <span class="romp-chip-kind romp-chip-question">question</span> — an answer is required.

The same mailbox is on the command line, for you and for scripts:

```bash
romp mail send --kind question api "Which auth approach did we settle on?"   # send, to the session named "api"
romp mail inbox                                                              # read this session's messages, and clear them
```

The full mail surface, shell and in-session, is in the
[Reference](reference.md#mail-from-the-terminal). Names resolve against the
currently live sessions; sending to a dead session's name errors instead of
silently parking mail.

## Sessions, revival, and search

A session outlives the conversations inside it. `/clear` starts the agent on a
blank slate, a relaunch starts it over, the kernel restarts: each of those is a
new conversation underneath, and `api` is still the same `api` on your board,
with its history and its cards.

Closed sessions come back. Click **+** and the closed ones are listed under
**Recent**; pick one and Romp offers to revive it, with its history intact, or
to open it read-only. Revival works by picking the session, not by its name, so
a new session that reuses an old name is a new session rather than the old one
resumed.

A session can also move to another folder. When the code it works on moves, say
a subproject that became its own repository, right-click its tab and choose
**Move to folder…** (or run `romp move <session> <dir>`): the conversation,
name, mail and history stay with the session, and from the next turn on the
agent works in the new folder and reads its `CLAUDE.md`.

A session's tab can carry one emoji before its name, so you can tell the
sessions apart at a glance by role or state: a moon on the one left running
overnight, a flag on the release manager. Right-click the tab and choose **Emoji…**
to open a picker: search by name or keyword, reuse one from the **Recent** row,
browse the categories, or type or paste one the list does not have. Or run
`romp emoji <session> <emoji>` (`romp emoji <session> --clear` removes it; with
no emoji argument it prints the current one). A session can also set or change
its own, with the `set_emoji` tool it gets alongside its mail tools, so you can
ask one to show a moon while it works unattended and a checkmark when it is
done. Exactly one emoji is accepted (a skin tone, a flag or a joined sequence
counts as one); letters, digits, a bare text symbol such as `©`, or a second
emoji are refused with the reason. The tab draws the emoji with the viewing
machine's own emoji font, so one from the newest Unicode release, accepted by
Romp, can still show as an empty box on a machine whose font predates it. The
emoji is stored with the session's name and color, so every dashboard shows the
same one, including a dashboard on another machine that has linked to this one.

A session started from another one joins its tags. Forking a session, breaking
a comment thread out into its own session, and running `romp new` inside a
session's shell all put the new session in the parent's groups, so a session's
children land beside it in the tab strip. `romp new --no-inherit` starts one
outside them; `romp new --in <tag>` names the tags directly (repeatable). The
**+** picker shows the tags of the tab you are looking at pre-selected in its
**Tags** row, where you can unpick or add before creating. Opening a name that
already runs inherits nothing: `romp new --in` still applies to it, while from
the picker, a name that already runs is focused and the Tags row is not applied
(a message says so; the row is a prefill, and applying it would move the
running session). Comment threads have no tab and inherit nothing until they
are broken out; `romp new` run inside a thread inherits from the session the
thread belongs to.

Search reaches inside sessions, not just across their names. As sessions run, a
lightweight index judge writes each one a headline and an abstract of what it
did, so searching for the work finds the session that did it, months later.

### Session backends

Sessions run on one of two backends, chosen per session:

- **SDK (the default, strongly recommended).** The kernel manages the Claude
  Code session through the Claude Agent SDK.
- **tmux.** A Claude Code session running in a terminal inside tmux. Run
  `romp new -t <name>` and that terminal session joins the interface like any other, so
  you can work in the terminal directly and still see it in Romp. The cost is
  that Romp has no direct connection to it: it reads what appears in the
  terminal and on disk, and sends messages and nudges by injecting keystrokes.
  That makes it less reliable and less responsive than the SDK, since scraping a
  terminal has edge cases a real API does not, and updates wait on the
  transcript reaching disk.

The two backends interleave freely, so terminal sessions and SDK sessions sit
side by side in the interface and message each other like any other pair.

## The Romp kernel (the back end)

The kernel is the program that runs your agents, watches their work, and serves
the user interface at `127.0.0.1:29855`. You run it on your own machine, with no
hosted service in between. Everything Romp stores stays local; the only traffic
that leaves your machine is `claude` itself, both the agents' own model calls and
the LLM calls in Romp's judge pipeline.

The kernel runs as a login service, so it is up whenever you are logged in. To
stop it on purpose, run `romp down`: it gives the agents a few seconds to
finish the turn they are on, then stops the kernel and keeps it stopped, and
`romp status` says so. `romp up` starts it again, and every session comes back
with its history; a session that was cut mid-turn is told so, and when, and
picks its work back up. `romp down --now` skips the wait; `romp down --wait 60`
lengthens it.

### Linking kernels on other machines

Romp kernels can connect and communicate across multiple machines, e.g. a laptop
and a server. This lets you control them all from one user interface, and lets
their agents communicate across the machines. A linked machine's sessions appear
as
<span class="romp-sid"><span class="host">server:</span>api</span> tabs and
timeline lanes beside your local ones, its cards share the feed, and its
sessions message yours, so an agent on your desktop can hand work to one on the
server.

You link machines from the network popover, which opens from the button at the
bottom right beside the settings gear:

![The network button](assets/guide/network-icon.png){ width="72" }

Every machine gets a row there with two controls. **Attach** brings that machine
into your interface: its sessions, its cards, and mail both ways over the one
connection. **Share my sessions there** puts your sessions in *its* interface,
for when you also work from that machine.

#### Attach a Romp kernel on another machine

Attach any machine you can `ssh` to, such as a server or a desktop that stays
on. Your kernel opens the connection.

1. **Install Romp on that machine**, the same way you installed it on your own
   (see [Install](install.md)).
2. **Check that `ssh <host>` connects without prompting you for anything.** Romp
   opens the connection in the background, so a password or passphrase prompt
   stops it; set up key-based login if you need to. Any target you could type
   after `ssh` works, including a `~/.ssh/config` alias.
3. **Attach it from your interface.** Open the network popover, click **+ Add a
   host**, type the ssh target, and click **Attach**.

The machine appears as a row with a live status, and Romp reads its kernel's
access token over ssh so your browser can authorize against it. A row reading
**kernel not answering** means no Romp kernel is running there: click **Start**,
which brings that machine's Romp up to date with this one's and boots it. Romp
never starts a remote kernel by itself, since a stopped one may be stopped on
purpose.
Detaching keeps the machine under **Previously attached**, so re-linking later
is one click and it returns with the trust level you last gave it.

#### Mail across linked machines

Each linked machine carries a trust level, set on its row, that decides what
happens to mail arriving from it:

- **trusted** — delivered straight to your sessions.
- **directed**, the default — held for your approval as a needs-you card.
- **isolated** — no mail either way; its sessions still appear in your
  interface.

Which to choose, and what each one guards against, is in
[Security and trust](#security-and-trust).

Machines that a linked machine can reach appear to you too, under **Reachable
via relay**: no tunnel of your own, their mail arriving one hop through the
machine in between. They carry the same trust selector as any host, because a
message is judged by where it came from rather than by the route it took.

When another machine is holding mail for approval, **Held for approval
elsewhere** shows you that it is, and how much, with the gist on hover. Acting
on a held message stays on the machine holding it, so this tells you where to
go rather than deciding for you.

Mail for a machine that is offline waits in an outbox and delivers when it comes
back. If it returns and the session you addressed is gone, that refusal comes
back to you. Every machine runs its own postal bus, so a laptop with no
connection at all still has full local messaging; linking only adds reach.

#### Also drive the fleet from the far machine

Attaching leaves the far machine's interface unaware of your sessions. Do this
only if you work from both computers, since mail already crosses both ways
without it.

If that machine can `ssh` to yours, it can just attach you and you are done. A
laptop usually cannot be reached that way: it moves between networks and sits
behind a router that accepts no incoming connections. Work from the laptop
instead:

1. **Attach the always-on machine** you want your sessions to appear on,
   following the steps above.
2. **Tick "Share my sessions there"** on that machine's row.

Your sessions now show up in its interface from whatever network you are on.
Because the laptop is the end that connects, the always-on machine never holds a
way in to it; untick the box and it forgets you. Romp calls this checking in,
and the always-on machine the hub, which is where `romp checkin` and
`romp checkout` get their names. Restarting Romp from the hub's interface
restarts the machines linked to it as well, and a checked-in machine is asked to
restart itself only: anything attached to that machine alone is restarted from
its own interface.

#### Hand the connection to a different machine

The add-host box has a **from** picker. Leave it on *this machine* and the
tunnel lives here, dropping when this kernel stops. Choose an attached host
instead and the attach is forwarded to that kernel, which dials out itself, so
the connection outlives your laptop. That machine needs its own ssh access to
the target.

The mechanics, including how the tunnels and the check-in handshake work, are in
[How Romp works](architecture.md).

## Remote access

You reach Romp in a browser tab, in the VS Code / Cursor extension, or from your
phone.

### From another machine

The kernel listens only on `127.0.0.1`, so a browser on another machine needs a
path to that port. Two paths work well; one common one does not.

**Plain ssh port forwarding.** From the machine with the browser:

```bash
ssh -N -L 29855:127.0.0.1:29855 <the machine running romp>
```

Then open `http://127.0.0.1:29855` as usual. OpenSSH forwards each browser
socket one-to-one and propagates closes, so a pane that goes away is gone on
both ends.

**Tailscale.** The same setup as for your phone below gives every device you
own a direct path; the dashboard is then a plain URL on your tailnet.

!!! warning "The VS Code port forwarder is not a good path for the browser dashboard"

    VS Code's Remote and Tunnels port forwarder multiplexes every forwarded
    socket over one channel and does not close the far end when the browser
    side goes away. The dashboard's panes are long-lived WebSockets that stream
    view updates, and each pane reconnects when it hears nothing for thirty
    seconds, so through that forwarder every reconnect left a dead connection
    behind on the kernel's side, all of them still receiving full view payloads
    over the one shared channel, and the live panes starved. One such incident
    counted 84 connections from three real panes.

    The kernel now protects itself: it pings every pane on each heartbeat and
    drops one whose ping goes unanswered, a reconnecting pane retires its own
    previous socket at once, and the timeline and feed cross the wire as
    deltas instead of whole payloads. That keeps a forwarded dashboard usable,
    but the forwarder still carries every byte over a channel it shares with
    your editor, so prefer one of the two paths above. The VS Code romp view
    is a different case: its sockets run on the kernel's own machine and close
    when a panel closes, so it never leaks connections, but under Remote or
    Tunnels the extension still relays each whole view payload to the local
    window as it changes. It does not yet take the deltas the browser panes do.
    A pane that falls 16 MB behind is dropped and reconnects on its own; the
    drop is logged in the kernel log and shows in the dashboard's bell, so a
    link that cannot keep up reads as what it is rather than as a flaky network.

### From your phone

The user interface is a web page, so your phone can run it against a kernel on
another machine. The obstacle is reaching that machine: the kernel listens only
on `127.0.0.1`, which your phone is not on.

[Tailscale](https://tailscale.com) closes that gap, and is free for personal
use. It puts your own devices on a private encrypted network, so your phone can
reach your laptop directly whatever network either one is on. Install it on both
devices and sign in to the same account on each.

In the Tailscale admin console, enable **HTTPS Certificates**, and leave
**MagicDNS** on (it is on by default): the `ts.net` certificate names come from
MagicDNS, so turning it off makes certificate provisioning fail in confusing
ways.

Three settings in the Tailscale app on the kernel's machine decide whether your
phone can reach it at all:

- **Allow incoming connections** must be on. Without it the machine joins the
  network but serves nothing to it, which reads as Romp being broken rather than
  as a Tailscale setting.
- **Use Tailscale DNS settings** must be on. This is MagicDNS on the client, and
  it is what makes the `ts.net` name resolve.
- **Launch Tailscale at login** is worth turning on. The proxy below survives a
  reboot, but it can only serve while Tailscale is running, so without this the
  machine drops off the network until you next open the app.

Then, on that same machine, one command opens Romp to your other devices:

```bash
tailscale serve --bg 29855
```

The bare-port form needs Tailscale 1.56 or newer; on older clients write
`tailscale serve https / http://127.0.0.1:29855`. On macOS the `tailscale`
command is not on your `PATH` until you enable **CLI integration** in the app's
settings.

Two commands go with it, for later rather than now. `tailscale serve status`
prints where the proxy currently points, which is the first thing to check when
a device cannot reach Romp. `tailscale serve reset` undoes the setup and returns
the machine to local-only, so run it when you want remote access off, not as
part of turning it on.

!!! warning "If you change the kernel's port"

    `tailscale serve` remembers the port you gave it, not whatever Romp is
    running on now. Change `ROMP_KERNEL_PORT` and the proxy goes on pointing at
    the old one, so the phone gets a dead page while everything looks healthy on
    the machine itself. Re-run `tailscale serve --bg <new port>` — it replaces
    the existing mapping rather than adding to it.

On the phone, open `https://<machine>.<tailnet>.ts.net/`. Romp answers with a
page asking for your access token; paste in the one `romp` prints. A
year-long cookie remembers the phone afterwards. Prefer this to putting
`?token=<token>` in the address, which works but leaves the token in your
browser history and in anything you share the link through. The cookie is itself
a credential, so only do this on a phone you control.

Only devices signed in to your Tailscale account can reach Romp: Tailscale
checks each device's identity and encrypts the traffic between them, and nothing
is exposed to your local network or to the internet. The proxy survives restarts
of both Tailscale and the kernel.

Two settings are worth changing while you are in the admin console. Turn on
**device approval**, so a new device has to be approved before it can join, and
leave key expiry enabled on the phone. Do not use `tailscale funnel`, the
public-internet variant: it would leave the token as the only thing between the
internet and your agents, with no device check in front of it.

!!! warning "If other people are on your tailnet"

    `tailscale serve` exposes Romp to **every** device on the tailnet, not just
    yours. On a family or team tailnet, the access token becomes the only thing
    standing between other members and your agents. Either keep the tailnet to
    your own devices, or write an ACL restricting the kernel machine to them.

#### Notifications on your phone

Romp can buzz your phone when a session needs you or finishes a task, so you can
put the phone down while the sessions work. On an iPhone, first add Romp to the
Home Screen (share sheet, then **Add to Home Screen**) and open it from there:
iOS only lets an installed app receive notifications, so in a plain Safari tab
the option stays off and says so. On Android and on a desktop browser the page
itself can receive them.

Then tap the bell. On a phone it sits in the bar along the bottom; on a desktop
it is in the bottom-right cluster. A small card opens with a main switch, two
switches indented under it, and a button:

- **Notifications** is the main switch. Off silences every device and the
  desktop of every machine you have attached; the bells on individual sessions
  and cards are mutes under it. While it is off, the two switches beneath it are
  dimmed but still work, so you can set a phone up first and switch everything
  on when you are ready.
- **This device**, under it, turns them on for the phone or browser you are
  holding. The first time, the browser asks for permission. If you refuse, the
  row goes grey and tells you where to allow it again (on an iPhone, Settings,
  then Notifications, then Romp; in a desktop browser, the site permission
  beside the address). Turning this off silences only this device. With the
  main switch off, the row says the device is set up but nothing arrives until
  the main switch is on.
- **Also when a turn finishes**, also under it, adds a notification every time
  any session finishes a turn, with the session's name and the first line of
  what it said. With many sessions running this is a lot of buzzing, so it is
  off unless you want it. A turn that ends by asking you something buzzes once,
  not twice.
- **Send a test notification** sends one notification to the device you are
  holding, whatever the switches say, and prints the push service's answer under
  the button, so you can see at once whether the phone is set up or why it is
  not. The test is addressed to the session you were looking at when you
  pressed the button, so you can switch to another session or another browser
  tab, tap the notification, and check that it brings you back. With the main
  switch off, the answer adds that real notifications will not arrive until it
  is on.

The handler that answers a tap lives on the phone, and the phone refreshes it
whenever you open the app and whenever a notification arrives. If a tap ever
opens Romp on the wrong session, close the app from the app switcher and open
it again once.

The bell itself shows the state of the device you are looking at: lit when the
main switch is on and this device is set up, and crossed out otherwise. Its
tooltip says which of the two is off.

## Security and trust

Romp drives agents that run tools and shell commands as you, so reaching its API
is equivalent to running code as you. Everything below follows from that.

**One token, required on every request.** The kernel and the postal bus both
demand a token on every request, local ones included. Loopback is not a
security boundary: on a multi-user machine every local account can reach your
ports, so without this any other user could inject prompts into your live
sessions. The token is 144-bit random and lives at
`~/.local/state/romp/serve-token` with mode `0600` (readable only by your own
user account). Local tools (the CLI, hooks, the bus, the editor extension) read
that file and send it automatically, so you never type it. Only liveness probes
(`/healthz`, `/version`, `/busy`, and the bus's `/ping`) are exempt.

The kernel and the bus mint that file when it is missing, one mint between them
under a sibling lock file, `serve-token.lock`. An existing token is never
replaced: a file left looser than `0600` is tightened at the next start (its
value is kept, so every client stays valid), and a token that exists but cannot
be read, or a symlink at that path, refuses to start instead of minting a
replacement nobody else holds. Under the service that refusal repeats in
`manager.log` every 10 seconds until you repair the file; the kernel then comes
back on its own.

A browser cannot read that file, which is why the link `romp` prints carries the
token in it. The first visit trades it for a year-long cookie, so the bare
`http://127.0.0.1:29855/` works from then on; `romp url` prints the link again
for a new browser or after clearing cookies. The cookie is a credential in its
own right, so treat a machine holding one as signed in.

**Remote machines.** Every machine mints its own token. When you attach a host,
your machine reads that host's token over ssh and stores it locally (in
`~/.local/state/romp/remotes.json`, also `0600`: it is a credential store).
Dashboard traffic to a remote never crosses the network in the open; it rides
the ssh tunnel, which supplies encryption and machine identity, while the token
authorizes at the far end. Checking a laptop in to a hub reverses which end opens
the connection, so credentials still flow outward from the machine that
initiates, and a hub never holds a way in.

**Trust levels for attached hosts.** Attaching two kernels lets their sessions
message each other, which means a session on the remote machine can put text
into a local session's context, and text in an agent's context can steer it. So
each host carries a trust level, set on its row in the network popover and
remembered per host. The level goes by where a message originated, not by the
route it travelled, so a machine whose mail reaches you relayed through a hub is
judged by the level you gave that machine:

- **trusted** — sessions on both machines message each other freely, as if they
  were on the same machine. For a machine you fully control.
- **directed** (the default for a newly attached host) — you can send work to
  its sessions, but its mail back to you is held for approval: each held message
  becomes a needs-you card with **Approve**, **Edit**, and **Deny**, so a person
  decides before that host's content reaches one of your agents. For rented or
  shared compute.
- **isolated** — no messaging in either direction. Its sessions still appear in
  your interface, but the two mail systems never connect. For gathering kernels
  that have nothing to do with each other into one place to work from.

**What this does not protect against.** Anyone with administrator access to a
machine can read any file on it, the token included, so don't keep long-lived
credentials on a machine you don't trust that far. Any program already running
under your own user account can read the token too, so two sessions on the same
machine are separated by policy rather than by this boundary. The lines Romp can
actually enforce are per-user (the token file) and per-machine (the trust
level).

Full details, including how to report a vulnerability, are in
[SECURITY.md](https://github.com/romp-on/romp/blob/main/SECURITY.md).

## How many tokens does Romp use?

Romp spends tokens on top of what you spend yourself. If you are running models
like Opus or Fable at high effort, the judging costs much less than the sessions
themselves. The analytics modal in settings separates your sessions from the
judge pipeline. The judge dollars are the exact cost each judge call reported;
the session dollars are the CLI's own per-turn cost from romp's spend ledger,
plus an estimate from transcript tokens and a price table for any part of the
period the ledger predates (the footnote names each amount; the estimate
stands alone only where there is no ledger). You can also reconfigure the
judges from the gear: the high-volume indexing tier defaults to Haiku, and the
judgment tier defaults to Sonnet.

The bottom bar's **API** cell, a dot and a word, shows how the API is treating
your sessions. Gray **ok** means no session is waiting on the API. Amber shows
how many sessions are waiting and names the problem: **rate limited**,
**overloaded**, **offline** (this machine cannot reach the API), or **errors**.
Red **paused** means auto-retry and the judges are stopped, and says why: a
usage limit, the monthly spend cap, or that you stopped them. Hover for the same
reading with the waiting sessions listed, and the history under it: the API's
state over the last 1, 5 and 15 minutes (attempts, the 429 and 5xx shares,
give-ups, sessions that retried) and the most recent state changes with how long
each held. A kernel restart shows as its own line there, because the counts
start over with the kernel. Click the cell, or press Enter on it,
for the detail: each waiting session (click one to open that session), a button
that stops auto-retry for every session while sessions are waiting and resumes
it while paused, and links to the usage figures and the Log.

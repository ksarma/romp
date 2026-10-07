#!/usr/bin/env python3
"""The phone layout's bottom bar (#mtabs) keeps every control on screen and under a finger at every phone width, in one
row from 360 to 430px, with Usage, Remote kernels and Restart kernel one tap away in the settings card (iOS item 4g,
2026-10-04 and 10-05).

THE BUG. The bar is one flex row: the pane tabs (each flex:1, never narrower than its label, 8px apart) and then the action
cluster, a divider and buttons that never shrink, each a glyph in 7px of side padding, 28 to 32px wide. There were six
(Usage, Remote kernels, Restart, the Log's triangle, the push bell and Settings), and the bell is not capability-gated (the
shell's push script reveals it on every page since it became the master switch), so it is always one of them. With the
default tabs (Chat, Sessions, Outline, Feed, Waiting) the row needed 418px in Chromium and 413px in WebKit and Firefox
(454 and 448px with the Files tab on), nothing in it could shrink or wrap, and the bar does not scroll (overflow visible,
in the shell's overflow:hidden body), so on a narrower window the cluster ran past the right edge of the screen out of
reach: at 390px Settings, at 360 the bell too, at 320 the Log's triangle as well, in all three engines.

THE FIX (kernel/kernel.py, the shell's markup and its phone media block; ui/webview/gear.js and gear.css, the settings
card). Two parts, as romp-manager ruled before round 1 (2026-10-05): keep ONE ROW where it can fit by moving actions, and
wrap only where it still cannot.
- The move. Usage, Remote kernels and Restart kernel left the bar. Usage and Remote kernels are its two panels about the
  machinery (spend and limits, other machines' kernels), not about the sessions; moving those two is the smallest move that
  gives one row from 375 to 430px in all three engines (measured at the wrap-only head by hiding each set of actions in the
  served bar: either one alone leaves 386px in Chromium; the two leave 354px in Chromium and 349 to 350px in WebKit and
  Firefox, and 390 and 384 to 385px with the Files tab on). Restart followed them (romp-manager's call 3, 2026-10-05): the
  kernel's restart is machinery too, rarely used and costly to hit by accident, and with it gone the default row needs 322px
  in Chromium and 318px in WebKit and Firefox (358 and 353px with the Files tab on), so the bar is one row at every phone
  width from 360px with the Files tab on or off. The bell stays on the bar. The three now sit in the settings card, a row of
  buttons under its title, above the tabs (so whichever tab the card opens at shows them), shown only on the phone layout
  and only where the shell publishes the marker beside the listener that runs them (window.__rompPhoneActs), so a phone
  shell still running a build from before the move, which has the three on its bar, gets no row whose taps run nothing.
  One click on the bar's Settings opens the card, one click on the button closes the card and runs the handler the bar's
  button ran (the shell's A-map, reached by a phoneAct message from the settings document, whose accepted acts are exactly
  the three), so Usage opens its modal, Remote kernels its panel and Restart kernel the kernel's restart (POST /restart), as
  before. They are buttons in a card, so they wear the card's button vocabulary, the dress of its other word buttons
  (Customize shortcuts' rules, copied), not the menu vocabulary of a dropdown's rows. The Remote kernels glyph keeps its
  live state there: the shell's /tunnels poll paints the card's copy as it painted the bar's (connected, attaching, each
  node's colour, the drop flash), and the card's opening brings it in step with the rail's glyph (the rail icon's live
  classes and the last poll's node colours; tests/test_remotes_panel_render.py holds that the opening paints nothing on the
  rail, so an Attach in flight keeps its busy there and the card shows it too). The drop flash plays only where the
  card is open at the drop: a closed card runs no animation, so the class a drop left on its copy is cleared when the card
  opens, where it would otherwise play the flash late. Usage explains rather than hides when it has nothing to show
  (romp-manager's call 6): the shell's usage panel opens only over a reading, so with none the card shows Usage disabled
  with the line "No reading yet" beside its name, and a tap on it leaves the card open (no engine dispatches a click for a
  pointer on a disabled button); the row's handler returns on a disabled button too, since a click a script dispatches
  on the button or its glyph, or click() on its label, reaches the handler in every engine (romp-manager's ruling after
  round 1 restored that check, which its call 3 had dropped); with a reading, Usage is enabled and opens the panel. The
  card reads the source the panel's opener reads: each opening asks the shell for a fresh pull
  (window.__rompUsagePull, the usage script's own fetch of its readings), Usage shows the romp loader and takes no tap until it ends, and
  then the card asks the usage script's own test over its readings (window.__rompUsageReading, the check the panel's opener
  makes); the shell's renderRows, the one writer of those readings, tells an open card on every change, so a reading that
  lands while the card is open shows at once; a shell that cannot be asked leaves Usage enabled with no line, as its bar
  button was. A read that failed is not a read that found no reading (romp-manager's rulings after round 1): where the
  shell's last read got an error status, no answer, or no answer before the card's pull's bound (an abort after 10 s,
  window.__rompUsageFailed telling the card), Usage shows the line "Couldn't load", never "No reading yet": disabled where
  the shell holds no reading, and enabled where it still holds one (a request with no answer leaves the readings as they
  were), its tap opening the panel over that reading (romp-manager's decision on round 1's builds). That tap opens the
  panel at once, whose age lines say how old the reading is, while the refresh runs behind it; the open panel follows the
  refresh's answer where it brings a reading; an answer that empties the readings (an error status) closes the open panel,
  its backdrop with it (romp-manager's ruling on round 2's pass: until then the content hid and the dimmed backdrop stayed
  up until a tap or Escape); and the refresh never opens the panel itself, so a panel closed before it ends stays closed
  (romp-manager's first rule at round 2: the tap had waited on its own pull, which carried no bound, with nothing on
  screen). Every read of the readings goes through the usage script's one bounded helper: the card's pull,
  the panel opener's, and the readout's click and 60 s refresh.
  Usage is one line tall in every state, as the row's other buttons are, and holds the loader's width (romp-manager's
  decision on round 1's builds), so loading to a reading, the common path, moves neither the row nor the tabs under it,
  and the row is no taller for Usage: the loader shows in the name's place, the two laid out in one cell, so Usage is
  106px wide in Chromium (104.94 in WebKit, 104.93 in Firefox) and 28.8px tall, loading and with a reading. A line saying
  what the reads found sits beside the name and widens Usage, so a pull that ends in one adds a line to the row on a
  narrow window, moving the tabs down 34.8px: from 344 to 368px in Chromium and from 341 to 364px in WebKit and Firefox
  (measured at every whole width from 320 to 430px, in both themes); at the other widths the row keeps its lines. The
  Remote kernels glyph wears the accent while a host is connected or
  attaching, on the glyph
  alone as on the rail, and the button's label keeps the card's text colour (PR 976's round 1, ui-3). The glyph sits on its
  button's own fill, which the button keeps on hover, its border still turning accent (round 1, extra6-2), and
  keeps its own colour there, so hover never turns an unlit glyph the lit one's accent (round 2, ui-1), and every colour it
  wears reads at 3:1 or more (a graphic, romp-manager's call 7) on the card and on that fill, at rest and
  hovered, in both themes: in the light theme its dialing grey and
  needs-you red are darker than the shell's (feed.css's --rn-wait and --rn-warn, #777777 and #db3d5a where the shell has
  #8a8a8a and #e5484d, which read 2.59 and 2.94:1 on that theme's button fill, #e7ded2). The red is turned in hue too,
  from the shell's 23 degrees to 15 in OKLCH, so it stays as far from the connected node's clay (#c2410c) as the shell's
  red is: 9.04 in OKLab distance x100, where the shell's has 8.94 (romp-manager's call 1 at round 1). Usage keeps its
  resting fill on hover too, as the Remote kernels button does, where the row's accent wash put its muted line at 4.38:1 in
  the dark theme, under the 4.5:1 text needs (romp-manager's first decision before round 2). And every label in the row
  keeps its resting colour on hover, the card's text colour set on each label by one rule for the row's buttons, where the
  row's hover colour, the accent, read 3.89:1 on the light theme's button fill under Usage's name and the Remote kernels
  label (romp-manager's ruling on round 2's pass) and 4.15:1 on the light theme's wash under Restart kernel's, under the
  4.5:1 text needs (romp-manager's ruling at the launch of round 3: the whole row, not a list of labels).
- The fallback. The action cluster is one element (.mtabs-acts) and the bar may wrap: where the tabs and the three actions
  left do not fit one row (below 322px in Chromium and 318px in WebKit and Firefox, so at 320px in Chromium and not in the
  other two; below 358px in Chromium and 353px in WebKit and Firefox with the Files tab on, so at 320px in all three), the
  cluster moves whole to a second row under the tabs, at the right edge, and the tabs take the full first row at the single
  row's height. A wrapped bar is taller, and its height can change
  with no resize at all (the Files tab turned on in the gear), so the shell re-measures the strip the panes leave for it
  whenever the bar's box changes (a ResizeObserver on the bar, beside the resize events that already re-measure it).
The desktop is untouched: the bar is display:none outside the phone media block, and the rail keeps its actions.

WHAT IS MEASURED, in the pages the kernel serves, in a real engine (tests/mtabs_fit_browser.mjs): the iPhone 14 descriptor
(Firefox without isMobile, which Playwright does not support there) at 320, 360, 375, 390, 414 and 430px wide in portrait
and the same phones in landscape, on the default tab set and with the Files tab on. Wherever the phone layout applies, for
every control the bar shows: its box wholly inside the window, the element at its centre is that control, no two controls
overlap, a tab's label fits inside it, every control keeps at least its natural width (its width in the unsqueezed row) and
the single row's height, the bar spans the window at its bottom edge and nothing in it overflows, and the strip the panes
leave (--mtabs-h) equals the bar's height with the shown pane ending above it. The bar shows three action buttons (the Log's
triangle, the bell, Settings) and no Usage, Remote kernels or Restart kernel. In portrait the bar IS one row on the default
set at 360, 375, 390, 414 and 430px and on the Files set at 375 to 430px (ONE_ROW: its natural width fits, every control on
it, the bar one control tall, so the panes keep all but that one row), and IS the fallback on the Files set at 320px
(FALLBACK: the natural row does not fit, the tabs fill the first row and the cluster sits together on the second at the
right edge). Elsewhere the bar is one row exactly where its natural one-row width (the bar laid out at max-content without
wrapping) fits. Then the Files tab turned on with no resize, at 340px where the default set fits one row and the Files set
does not: the bar wraps and the strip follows it. Then the moved actions, at 390px: the bar's Settings clicked at its centre
opens the card; its row of three buttons shows, each wholly in the window and the card and hit at its centre, and each
wearing Customize shortcuts' dress at rest (its computed fill, hairline, radius, text colour, padding, font and press
transition equal #rs-keys-btn's, the Remote kernels button's text colour too while the poll lights its glyph, read once
Usage's colour transition ends), Usage enabled with its line hidden (the lab's reading); the Remote kernels glyph wears the
state the shell's poll painted on the rail's glyph (the shell's own GET /tunnels answers two synthetic hosts, one connected
and one with no kernel: the glyph on, its nodes needs you and connected, the same classes, colours and fills as the rail's);
the shell's next poll is held until after the first opening, so the card's paint is the opening's own, and when it is
released with both hosts connected the card's copy follows it; then one click on Usage closes the card and opens the Usage
modal (the lab's usage.json makes it a spend reading, so the panel has something to show), and after the bar's Settings
again, one click on Remote kernels closes the card and opens the Remote kernels panel, and after it again, one click on
Restart kernel closes the card and makes the shell's one POST /restart (the driver answers it with a refusal in the
manager's shape, RESTART_REFUSAL, so the lab kernel stays up, and the shell's handler takes it: its splash down, the
refusal's words on the rail's restart button); no click but that one makes a POST /restart. Then the drop cue (TUNNELS_DROP,
a host that was up answering with no kernel): with the card closed the poll drops the host, and at the card's next opening
its glyph carries no flash; then the host comes back and drops again with the card open, and the glyph's flash runs; then
the host comes back again, the Token usage panel opens over the card (#ra-open, which hides the card with no message to the
shell), the host drops while the panel is up, the panel closes (#ra-close), and two frames after the card shows again its
glyph carries no flash. Then the glyph's states, on the same page: with the card open, a poll that turns the host with no
kernel to attaching (TUNNELS_ATTACH) marks the card's glyph lit and busy as the rail's is, its connector path's computed
animation rs-pact-march running over dashes of 3 and 3 (by value); the hosts settled (TUNNELS_DROP again) take busy and the
march off; a poll with no host (TUNNELS_NONE) leaves the glyph unlit with the card open; and with the hosts back up and the
card closed, the same poll leaves the glyph unlit at the card's next opening. Then
Usage with no reading, on a page whose shell's usage pull (its GET under /usage/) answers no rows (the rail's readout, which
renders over the readings, read empty as the leg's premise): the card opened from the bar's Settings shows Usage disabled
with the line USAGE_NONE once the opening's ask for a fresh reading has ended, its name in the disabled button's own
colour; a click at its centre leaves the card open, opens no Usage modal and posts no phoneAct (read after a settle: an absence has no event to wait on), and the line still
shows; a script's clicks on it, click() on its label and a click event dispatched on the button and on its glyph, each
leave the card open, open no Usage modal and post no phoneAct; then, the card still open, a reading arrives (the lab's
own GET /usage payload posted to the shell as the timeline
posts it, the shell's later pulls let through), and the open card shows Usage enabled with no line; the readings emptied (a
payload with no window and no spend, posted the same way) show it disabled with its line in the open card, filled again
enabled with no line; then the Token usage panel over the card (#ra-open, which hides the card with no word to the shell),
each turn from an opening: with the readings filled (Usage enabled), the readings emptied while the panel is up and the panel
closed (#ra-close) show Usage disabled with its line in the card the close shows; from an opening with no reading (Usage
disabled), the readings filled while the panel is up show it enabled with no line after the close; and one click closes the
card, posts phoneAct usage and opens the Usage modal. Then a reading the kernel holds and the shell has not pulled, on a page
of its own at 390px: the shell's boot pull answers no rows and every later pull reaches the lab, with the Sessions pane
unloaded so no timeline forwards a reading (both read as the premise); the card's opening asks the shell for a pull (a GET
under /usage/ after the opening), and while that request is held Usage shows the romp loader in its name's place (the
swirl spinning, the wordmark, the dots pulsing, the name unseen), disabled and busy, with no line, and a tap at its centre
leaves the card open and posts no phoneAct; let through, the ask ends with Usage
enabled, no line and no loader, its name seen, and one click closes the card, posts phoneAct usage and opens the Usage modal. Then the
reads that fail, on a page of its own at 390px, the shell's boot pull answering no rows (the readout read empty as the
premise): the card opened over an opening's pull the driver answers with ERROR_STATUS, over one it aborts in transit,
and over one it holds unanswered under a bound of HANG_MS set on the shell (window.__rompUsagePullMs; the loader read
while it is held, and its end read at least HANG_MS and at most HANG_WAIT_MS after the click), shows Usage disabled with
the line USAGE_ERR and not USAGE_NONE once each ask has ended, the card open and nothing posted; after each of the
three, an opening whose pull the driver answers ok with no rows shows Usage disabled with USAGE_NONE and not USAGE_ERR (an
ok answer clears the failure, and the next failure starts from a read that did not fail). Then the reopen race, three
times: the card opened over a pull the driver holds, closed, and opened again over a later pull, and the held pull ended
after that one. The later pull answered with no rows and the held one failed in transit; the later one failed in transit
and the held one was let through to the lab's reading; the later one reached the lab and the held one answered with
ERROR_STATUS. Once the held pull's end has run in the shell, Usage keeps the later pull's answer in the first and the
third, USAGE_NONE alone and enabled with neither line, and in the second the held pull's ok answer still writes its
reading, which fills the readout, and Usage is enabled beside USAGE_ERR, the later pull's failure kept (romp-manager's
decision 6 on round 1's builds); in each, Usage read once more through the card's own surface (the shell's layout word,
which the open card answers by reading Usage afresh, read once a probe word posted after it has arrived) is the same, and
the shell's flag (window.__rompUsageFailed) is the later pull's (a wrapper over window.__rompUsagePull records the order
the two end in, and RACE_MS set on the shell keeps the held pull from ending on its own bound). Then an opening over ERROR_STATUS (the readings emptied,
Usage disabled beside USAGE_ERR), the card left open, and the lab's own GET /usage payload posted to the shell as the
timeline posts it: once the readout fills, Usage is enabled with neither line, the forward being a read too. And an
opening whose pull reaches the lab then shows Usage enabled with neither line; then, the shell holding that reading, an opening whose
pull fails in transit shows Usage enabled with the line USAGE_ERR beside its name, seen, its left edge at or past the
name's right edge and the loader out of the layout (its computed display none), and not USAGE_NONE, the card open and
nothing posted,
and one click on Usage closes the card, posts phoneAct usage and opens the Usage modal over that reading. Then the tap
opening the panel at once: the modal closed, the shell given a window reading of its own (a pull the driver answers with a
synthetic five-hour window reported ten minutes before, read at an opening), the card opened over a pull held past HANG_MS,
which the bound ends (Usage enabled beside USAGE_ERR, the reading kept), the bound raised to RACE_MS, and Usage clicked
with the tap's own pull held: the Usage modal is up within 1 s of the click over that reading, its window section and its
age line (updated 10m ago), and once the held pull is answered with a fresher reading of the same window, reported then,
the open modal follows it (updated just now), its By session button the node it was before. And the refresh behind that
panel never opens it: the card's pull held past HANG_MS again (Usage enabled beside USAGE_ERR), Usage clicked with the
tap's own pull held, the modal up within 1 s and then closed while that pull is held, and once the pull's fresher answer
has run in the shell (its flag cleared) the modal is still closed, the backdrop off. And a refresh that empties the
readings closes that panel: the card's pull held past HANG_MS again, Usage clicked with the tap's own pull held, the modal
up within 1 s and left open, and that pull answered with ERROR_STATUS; once the shell's readings have emptied, the modal is
closed, the backdrop off (its class, and its computed display none), the close hook cleared, and the element at the
window's centre not the backdrop. Then the deploy
skew, on a page of its own at 390px:
the shell publishes its marker (window.__rompPhoneActs) and the card opened
from the bar's Settings shows its row; with the marker deleted (the phone layout and no marker, as a shell from before the
move has) the card opened shows no row (not displayed, its buttons boxless); and with the marker back and the usage script's
two names deleted (__rompUsageReading and __rompUsagePull, a shell that cannot be asked) the card's Usage is enabled with no
line; then, the card open with its row and the marker deleted (so a layout word the card acts on hides the row), the
shell's layout word ({romp:'link'}) posted from the settings frame's own window and from the chat pane's window leaves
the row shown, each read once a probe word posted after it from the same window has arrived, and the same word from the
shell's window hides it (the control), and with the marker back shows it again. Then the row following the layout while
the card is open, on a page of its own in a plain context (a fine pointer, so
the layout turns at 820px), the shell's poll answering both hosts up: the card opened at 390px shows its row; the window
widened to WIDE with the card open hides it (not displayed, its buttons boxless), a host drops there (the class left on the
hidden glyph, the premise), and the window narrowed to 390px again shows the row, its glyph carrying no flash two frames on,
and Usage enabled with no line once the ask the row's return makes has ended; then the same turns under the Token usage
panel: opened over the card with its row at 390px, the window widened to WIDE while it is up (the shell's layout turned, the
premise) and the panel closed, the card it shows has no row; the card opened again at WIDE (no row, read at the opening), the
panel opened, the window narrowed to 390px while it is up and the panel closed, the card shows the row, and Usage enabled
with no line once its ask has ended. Then the
Remote kernels glyph's colours in the dark and the light theme (THEMES), each on a page of its own at 390px: in the card
opened from the bar's Settings, every colour the glyph can wear (GLYPH: the glyph lit and attaching, read on its svg, a node connected,
dialing and needs you) reads at GLYPH_FLOOR or more against the card's background and against the button's fill, each
colour read with its class set and the element's transitions off; and again with the pointer moved onto the button (its
transitions off), against the fill it wears hovered, :hover read as the premise, and the unlit glyph (its svg's colour with
neither class) wears the same colour hovered as at rest, and so does the button's label, which reads TEXT_FLOOR or more on
that fill; and the needs-you red stays
SEPARATION_FLOOR or more from the connected node's colour in OKLab; then, on the same page, the card opened again over
the opening's pull held (the loader up, the shell's bound set to RACE_MS meanwhile) with the window taken through the
portrait widths (HEIGHT_WIDTHS), then the pull let through to the lab's reading and the widths taken again: at each, the
row's height, Usage's width and height, and the tabs' offset in the card and their top in the window are the same loading
and with the reading, to SAME px, and Usage is as tall as Restart kernel (on another line of the row there) in both; in
both, too, Usage holds the loader's width: its words are as wide as the loader's laid-out box, and Usage as wide as its
glyph and those words with the gap between them, its side padding and its borders, both to SAME px, and it is narrower
than it is over no rows and over ERROR_STATUS (those two states read at the same widths, and compared only for that); and
Usage's name is unseen while loading and seen with the reading and beside either line, each line's left edge at or past the name's right edge and the loader
out of the layout (its computed display none) while a line shows. Then the card opened over the lab's
reading and again over a pull the driver aborts in transit (Usage enabled beside USAGE_ERR), Usage's name read with the
pointer off the row, and the pointer moved onto Usage with its transitions off: the line reads TEXT_FLOOR or more on the
fill Usage wears hovered, :hover read as the premise, and the name wears its colour at rest and reads TEXT_FLOOR or more
on that fill. Then the card opened over the lab's reading again, and every button the row holds, listed from the page (so
a button added to the row later is read too; the three in MOVED must be among them), hovered in turn from off the row with
its transitions off, enabled and holding :hover as the premise: each label, every visible, laid-out element holding words of
its text, reads TEXT_FLOOR or more on the fill its button wears hovered, each composited through the backgrounds and
opacities out to the first opaque background (romp-manager's ruling at the launch of round 3, item 1). Then a desktop
window, where the bar is hidden, and the desktop rail at 821 and 1100px, whose actions (restart, Remote kernels, the
bell,
the gear) and their boxes equal af7d18250's (RAIL_AF7 below), and where the settings card, opened from the rail's gear
clicked at its centre, shows no row of moved actions (not displayed, its buttons boxless: the rail has its own).
MTABS_FIT_DUMP, a directory, keeps each engine's raw readings there.

Red at the wrap-only head, in all three engines: its bar shows six actions, it wraps where one row is owed (at 375 and
390px, and at 414 in Chromium; its row fits 414 in WebKit and Firefox and 430 in all three), and its card has no row of
moved actions. Red at the two-action move (Usage and Remote kernels moved, Restart still on the bar), in all three engines:
its bar shows Restart, its Files set wraps at 375px, and its card has no Restart kernel button. The phoneAct pin is red
under the listener's old accepted set (net and usage alone): the card's Restart kernel closes the card and no POST /restart
follows. The button dress's pin is red at the menu dress the row wore before (the menu card's fill, a 6px radius, 5px 10px
of padding, 12px text), and where the accent lights the whole Remote kernels button, its label too (the rule before round
1's ui-3). The no-reading pins are red at the card without that state (Usage enabled with no reading, and its
tap closing the card to open nothing); the reading landing in the open card is red where the card reads the state only when
it opens, and the emptying where the shell's renderRows tells the card only as it fills its readings; the unpulled reading is red where the card answers from the shell's cached readings without a pull (Usage
disabled with its line, no loader, the tap opening nothing). Both taps on a disabled Usage, with no reading and while the
opening's pull is out, are red under a mutant that never disables it; a script's clicks on a disabled Usage are red
without the row handler's check of the disabled state (each closes the card and posts phoneAct usage). The failed reads
are red where an error status reads as no reading and a failure leaves the line as it was (No reading yet after the
error status and after the abort in transit), and the hung pull where the card's pull carries no bound (the loader still
up) and where it leaves the override unread and aborts at the kernel's 10 s (the loader still up HANG_WAIT_MS after the
click). With the ok answers between the failures, the abort in transit and the hung pull are red under a mutant whose failed
path leaves the flag as it was (No reading yet after each), and the three ok answers under a mutant where an ok answer
leaves a flag a failure set (Couldn't load after each). The failed read over a cached reading is red where the card says
Couldn't load only over no reading (Usage enabled with neither line). The reopen race is red where every read's end writes the flag,
and an error status empties the readings, whichever later read has ended: Usage turns from No reading yet to Couldn't
load, from disabled beside Couldn't load to enabled with neither line, and from enabled to Couldn't load (in Chromium); and
each turn is red under a mutant that drops one of the three checks, the failed path's (the first turn), the answer's flag
write (the second, Usage enabled with neither line, and the third's read through the card's surface, where the outdated
error status set the flag and told no card: Couldn't load, the flag true) and the error status's return (the third, No
reading yet: the readings emptied). The second turn is red too under a mutant that drops every outdated answer
(`else return;`: the readout empty and Usage disabled beside Couldn't load), and the first turn's read through the card's
surface under one whose late failure sets the flag and skips only the card's tell (Couldn't load there and the flag true,
where the card's own read still shows No reading yet), in Chromium. The forward after a failed read is red without the
forward's clear of the flag (Usage enabled beside USAGE_ERR once the readout fills, in Chromium). The tap opening at once
is red where the tap's own pull ran before the panel opened, with no bound (nothing open 1 s after the click, in
Chromium, WebKit and Firefox); its follow under a mutant whose renderRows leaves an open panel as it is (the modal still
says updated 10m ago); and its button where the repaint rebuilds the whole panel (the By session button replaced), in
Chromium. The closed panel is red under a mutant whose refresh behind the panel opens it on its end (the modal up again
once the held pull's answer has run, in Chromium), and where the tap's own pull ran before the panel opened, with no
bound (nothing open 1 s after the click, then the modal opened by that pull's answer, in Chromium, WebKit and Firefox).
The emptied panel is red at the head round 2's pass built, where renderRows' empty exit hid the panel's content alone
(the backdrop still on, its computed display block, the close hook set and the backdrop the element at the window's
centre, in Chromium, WebKit and Firefox).
The row and the tabs are red where Usage keeps two
lines' height in every state (Usage 43.64px tall, 43.65 in Firefox, where Restart kernel is 28.8, at every width in both
themes); under a
mutant that lays the loader out only while it shows (Usage 106px wide loading and 82 with a reading at every width, and at
320px the row a line shorter with the reading, in Chromium); and under one that lays it under the name (Usage 43.64px tall
loading, so the row is 14.85px taller loading than with the reading from 360px, and a line and that much taller at 320px,
in Chromium). Usage's width is red where its words are as wide as its widest line in every state (in all three engines, at
every width in both themes: the words 80px wide where the loader is 64 in Chromium, 76.36 where it is 62.94 in WebKit and
76.38 where it is 62.93 in Firefox, and Usage as wide loading and with a reading as with either line, 122, 118.36 and
118.38px); and in Chromium under five mutants of gear.css: both lines laid out unseen beside the name (the words 150px wide,
Usage 192 where No reading yet makes it 168), Usage given No reading yet's width as its least (168px, where its parts come
to 106, and no narrower than with either line), a least width of 130px (its parts' check alone), the words given a least
width of 80px (the words' check alone), and the loader one of 126px (Usage 168px loading and with a reading, as wide as with
No reading yet: the check that it is narrower, alone). The name is red where it stays seen while the loader shows (in all
three engines, at every width in both themes and over the unpulled reading), and in Chromium under a mutant that drops the
rule hiding it while Usage is busy (the same lines) and one that hides it in every state (unseen with a reading, beside
either line, after the unpulled reading's pull and over the cached reading). The line's place is red in Chromium under a
mutant of gear.css that drops the line's own grid cell (the line over the name, its left edge 34 px inside the name's right
edge, at every width in both themes and over the cached reading), and the loader's display under one that drops the rule
taking the loader out of the layout while a line shows (display flex, in the same reads). The layout word's source is red under a mutant of the card's link listener
that does not check the word's source (the row hidden by the settings frame's own word and by the chat pane's). The
fallback's pin is red under the old rule restored (no wrap), and the
rail's under the move applied to the rail as well; the desktop card's under a mutant that shows the row on every layout
(romp-manager's call 8). The drop cue's pin is red at the commit before its fix, where a drop that came while the card was
closed flashed the glyph at the card's next opening; the Token usage panel's is red without the panel close's clear of the
class (gear.js raHide), where the glyph flashed as the panel closed. The glyph's states are red under mutants of their
paint: busy no longer toggled on the card's copy (the busy line, and the march line with it), the march rule gone from
gear.css (the march line), the copy's lit class added by the poll and never taken off (the open card's unlit line), and the
opening's copy of that class made the same way as well (both unlit lines). The deploy skew's pins are red where the shell
publishes no marker, where the card reads the layout alone (its row shown with no marker), and where a shell that cannot be
asked reads as one with no reading (Usage disabled with its line). The layout leg is red where the card reads the layout
only when it opens (the row still shown in the widened window), and its glyph line red without the clear of the drop's class
when the row shows again (the flash then plays at the narrowing). The Token usage panel's turns, in both legs, are red where
the card follows the readings and the layout only while it shows, and where it follows them only when it opens: the card
the panel's close shows keeps Usage and the row as they were when the panel opened. The narrowing's Usage line is red under
a mutant whose ask stands down when it ends while the card is hidden (the loader stays). The contrast pin is red at the shell's literals in the light theme, in
all three engines: the dialing grey #8a8a8a reads 2.59:1 and the needs-you red #e5484d 2.94:1 on the button's fill; its
hovered half is red where the button takes the row's accent wash on hover, on which the dark needs-you red reads 2.95:1;
and the separation's pin is red at the darker red the light theme had at the shell's hue, #dc3f46, 7.10 from the clay. At
the head round 2 reviewed, in Chromium, WebKit and Firefox, the unlit glyph's hovered colour is red, the button's hover
colour reaching it (rgb(156, 210, 255) hovered where it is rgb(204, 204, 204) at rest in the dark theme, rgb(194, 65, 12)
where it is rgb(31, 30, 29) in the light one), and the hovered Usage's line is red where Usage takes the row's accent wash
on hover (4.38:1 in the dark theme; 5.44 on the resting fill, and 5.37 in the light theme). At the head round 2's pass
built, in Chromium, WebKit and Firefox, both labels' hovered colour is red, the row's hover colour reaching them
(rgb(156, 210, 255) hovered where they are rgb(204, 204, 204) at rest in the dark theme, rgb(194, 65, 12) where they are
rgb(31, 30, 29) in the light one, which reads 3.89:1 on the hovered fill #e7ded2, under TEXT_FLOOR). In Chromium, a
mutant of gear.css's label rule that drops either label turns that label's reads red and the other's not, and one whose
rule does not skip a disabled Usage turns the no-reading leg's name red (rgb(204, 204, 204), the card's text colour,
where the disabled button wears rgb(110, 118, 129)). At the head round 3 reviews, in Chromium, WebKit and Firefox,
the read of every button in the row is red on Restart kernel's label alone, in the light theme alone, the one label the
row's hover colour still reached: rgb(194, 65, 12), 4.15:1 on its hovered wash #f4e3d7, under TEXT_FLOOR.
Runs in the "Browser-backed served-page tests (pytest)" step of the
served-pages job, "Served pages (pytest, ubuntu-latest)" (ci.yml, ROMP_SERVED_TESTS_REQUIRE=1: a skip here is a failure), in
Chromium; the WebKit and Firefox legs are `optional:` skips where that engine is absent or not declared in
ROMP_SERVED_TESTS_ENGINES (CI declares chromium; a developer's box runs all three).

The lab: one kernel from test_ship_reship_served.kernel_env (a private XDG root, `session-hosts` floored off,
ROMP_MANAGER_PORT=1, no catalog or update fetch, a hermetic postal bus), its port from tests/lab_ports.py and proved its own
there, a private dist (lab_dist.copy_dist), no sessions, and a usage.json that marks the machine as an API-key one (the
Usage modal's spend reading, zeros). The driver asserts /healthz on the lab's port before any request. Synthetic throughout.
"""
import json
import lab_dist
import lab_ports
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(HERE)
BIN = os.path.join(ROOT, "bin")
EXT = os.path.join(ROOT, "vscode-extension")
sys.path.insert(0, HERE)
import test_ship_reship_served as _lab   # noqa: E402  (kernel_env: every lab kernel's environment; the module, not its classes)

# Hermetic state BEFORE anything: this module loads no romp code in-process (the kernel is a subprocess under kernel_env's
# roots), but the floor costs two lines and a later edit that adds a load must not write real state.
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor
os.makedirs(os.path.join(os.environ["XDG_STATE_HOME"], "romp"), exist_ok=True)
Path(os.environ["XDG_STATE_HOME"], "romp", "session-hosts").write_text("off\n")   # the Testing rule for a test that mints its own root

DRIVER = os.path.join(HERE, "mtabs_fit_browser.mjs")
# the phones: width by height in portrait (320 the narrowest, 430 the widest), and the same phones turned to landscape
PORTRAIT = ((320, 568), (360, 640), (375, 667), (390, 844), (414, 896), (430, 932))
LANDSCAPE = tuple((h, w) for w, h in PORTRAIT)
# the portrait widths where each tab set is ONE row in every engine: the ruling's 375 to 430px, and 360 for the default set,
# whose row needs 322px at most (measured in the three engines); the Files set needs 358px at most, 2px inside 360, so 360 is
# a measured figure for it and not a pin (the gear's glyph is a fallback font's, whose width can differ between machines)
ONE_ROW = {"default": (360, 375, 390, 414, 430), "files": (375, 390, 414, 430)}
FALLBACK = {"files": 320}   # ...and the two-row fallback, owed in every engine: the Files set at 320px (the default set's row
                            # fits 320 in WebKit and Firefox and not in Chromium, so its shape there is held by the natural row)
DYNAMIC = (340, 640)   # the default tabs fit one row here and the Files set does not (asserted, so the leg proves a wrap)
ACTS = (390, 844)      # the phone the moved actions are clicked on
MOVED = ("usage", "net", "restart")        # the three actions that left the bar for the settings card, in the card's order
BAR_ACTS = ("merr", "mbell", "settings")   # the three left on it, in their order
# the lab's answer to the shell's POST /restart in the moved-actions leg (the driver answers it; the kernel never sees it): the
# manager's refusal shape, so the shell's restart handler runs to its end (splash down, these words on the rail's button)
RESTART_REFUSAL = "synthetic refusal: the lab kernel stays up"
USAGE_NONE = "No reading yet"   # the card's line beside a disabled Usage's name (gear.js), the words a person reads
USAGE_ERR = "Couldn't load"     # ...and its line there where the shell's last read of the readings failed
ERROR_STATUS = 500   # the kernel's answer to the opening's pull where a leg needs an error status (the driver answers it)
# the bound the failed-read leg sets on the shell's pull (window.__rompUsagePullMs) for the pull it never answers, in ms: the
# kernel's own is 10 s, which each engine's leg would otherwise wait out; and how long after the click the leg waits for the
# bound to end the loader, well under that 10 s, so an end only the default makes (an override the pull does not apply) reads
# as hung (romp-manager's decision on PR 976's round 1 builds; ui/webview/usage-pull-bound.test.ts holds the default itself)
HANG_MS = 1500
HANG_WAIT_MS = 5000
# ...and the bound it sets for the reopen race, in ms: long enough that the held pull ends only when the driver ends it
RACE_MS = 60000
SAME = 0.01   # px: the row and the tabs loading and with a reading are equal by construction (the same layout), so compared exactly;
              # so are Usage's words and the loader's box, and Usage's width and its parts' sum (the same layout's own boxes)
HEIGHT_WIDTHS = tuple(w for w, _ in PORTRAIT)   # ...at each phone width in portrait, where the row wraps
# the themes the Remote kernels glyph's colours are measured in, by the gear's theme ids: the dark default and the light theme
# (no rule in feed.css or gear.css reads the Yatharth dark theme's class, so the default stands for both dark themes)
THEMES = (("dark", "classic"), ("light", "yatharth-light"))
GLYPH = ("lit", "attaching", "connected", "dialing", "needs you")   # every colour the glyph can wear, as the driver names them
GLYPH_FLOOR = 3.0   # the contrast a graphic needs (WCAG's non-text 3:1), against the card's background and the button's fill
TEXT_FLOOR = 4.5    # ...and the contrast text needs (WCAG's 4.5:1 for text at the card's sizes): Usage's line on its hovered fill
# ...and how far the needs-you red stays from the connected node's colour, as OKLab distance x100 (romp-manager's call 1 at
# PR 976's round 1): at least the separation the shell's own pair has in the light theme, #e5484d from the clay #c2410c,
# 8.94, so the light card's darker red tells the two states apart no worse than the shell does (the same red darker at the
# shell's hue was 7.10)
SEPARATION_FLOOR = 8.9
DESKTOP = (1280, 800)
WIDE = (900, 844)   # the window the layout leg widens to with the card open: past the phone query's 820px, in a fine-pointer context
RAIL = ((821, 800), (1100, 800))   # the desktop rail: just past the phone query's 820px, and a laptop
# the shell's own /tunnels poll in the moved-actions leg: two synthetic hosts, one connected and one with no kernel (the glyph
# on, its nodes the worst two: needs you, connected), then both connected (every node connected)
TUNNELS = {"tunnels": [{"host": "TESTHOST", "status": "up"}, {"host": "PEERHOST", "status": "no-kernel"}],
           "peersMode": False, "autoUpdate": False, "local": {"host": "", "ver": "", "sha": ""}}
TUNNELS2 = {"tunnels": [{"host": "TESTHOST", "status": "up"}, {"host": "PEERHOST", "status": "up"}],
            "peersMode": False, "autoUpdate": False, "local": {"host": "", "ver": "", "sha": ""}}
# ...and the drop: PEERHOST, up in TUNNELS2, answers with no kernel, so that poll is a host dropping (the glyph's flash)
TUNNELS_DROP = {"tunnels": [{"host": "TESTHOST", "status": "up"}, {"host": "PEERHOST", "status": "no-kernel"}],
                "peersMode": False, "autoUpdate": False, "local": {"host": "", "ver": "", "sha": ""}}
# ...the attach: PEERHOST, with no kernel in TUNNELS_DROP, connecting (a status the shell reads as in flight), so that poll
# turns the glyph busy with no drop (the drop cue fires only for a host that was up)
TUNNELS_ATTACH = {"tunnels": [{"host": "TESTHOST", "status": "up"}, {"host": "PEERHOST", "status": "connecting"}],
                  "peersMode": False, "autoUpdate": False, "local": {"host": "", "ver": "", "sha": ""}}
# ...and no host at all: the glyph unlit, its nodes unpainted; an empty list drops no host either
TUNNELS_NONE = {"tunnels": [], "peersMode": False, "autoUpdate": False, "local": {"host": "", "ver": "", "sha": ""}}
# The desktop rail at af7d18250 (fork main, before this PR), read by this module's driver against that tree in this lab: the
# shown actions in order, each with its width, height and top, and its left and right edges as offsets from the gear's left
# edge; for the gear itself its right edge as an offset from the window's right edge, its top and height. The gear is a text
# glyph (U+26ED) that Inter does not carry, so its width is a fallback font's and differs between engines (15, 15.2 and
# 15.37px) and can differ between machines; holding the others from its left edge keeps every other quantity exact. The
# values were the same in Chromium, WebKit and Firefox and at both widths (821x800 and 1100x800).
RAIL_AF7 = (
    {"id": "rail-refresh", "w": 18, "h": 26, "top": 772.5, "left": -96, "right": -78},
    {"id": "rail-net", "w": 18, "h": 26, "top": 772.5, "left": -64, "right": -46},
    {"id": "rail-bell", "w": 18, "h": 26, "top": 772.5, "left": -32, "right": -14},
    {"id": "rail-gear", "h": 27, "top": 772, "right": -19},
)
DUMP = os.environ.get("MTABS_FIT_DUMP", "")   # a directory: each engine's raw readings are copied there (evidence for a run)
EPS = 0.5


def _num(v):
    """A measured number: an int or a float, never a bool (JSON's true is not a width)."""
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _px(v):
    """'31px' -> 31.0; an empty or malformed value is a failure, not a zero."""
    v = (v or "").strip()
    assert v.endswith("px"), "not a px value: %r" % (v,)
    return float(v[:-2])


def _problems(where, row):
    """Every way the bar fails one reading, as lines naming the controls; empty when the bar holds."""
    out = []
    vw, vh, bar, cs = row["vw"], row["vh"], row["bar"], row["controls"]
    past = [c["key"] for c in cs if c["left"] < -EPS or c["right"] > vw + EPS]
    if past:
        out.append("%s: past the window's edge (%dpx): %s (rights %s)" % (
            where, vw, ", ".join(past), ", ".join("%g" % c["right"] for c in cs if c["key"] in past)))
    missed = [c["key"] for c in cs if not c["hit"]]
    if missed:
        out.append("%s: the element at the centre is not the control: %s" % (where, ", ".join(missed)))
    for i, a in enumerate(cs):
        for b in cs[i + 1:]:
            if min(a["right"], b["right"]) - max(a["left"], b["left"]) > EPS and min(a["bottom"], b["bottom"]) - max(a["top"], b["top"]) > EPS:
                out.append("%s: %s and %s overlap" % (where, a["key"], b["key"]))
    clipped = [c["key"] for c in cs if c["tab"] and not c["labelFits"]]
    if clipped:
        out.append("%s: a tab's label is wider than the tab: %s" % (where, ", ".join(clipped)))
    if abs(bar["left"]) > EPS or abs(bar["right"] - vw) > EPS or abs(bar["bottom"] - vh) > EPS:
        out.append("%s: the bar does not span the window at its bottom edge: %r" % (where, bar))
    if bar["scrollW"] > bar["clientW"] + EPS:
        out.append("%s: the bar's content overflows it (scrollWidth %s, clientWidth %s)" % (where, bar["scrollW"], bar["clientW"]))
    if row["docScrollW"] > vw + EPS:
        out.append("%s: the document is wider than the window (%s)" % (where, row["docScrollW"]))
    acts = [c for c in cs if not c["tab"]]
    one_h = max((c["h"] for c in acts), default=0)
    narrow = ["%s (%g, natural %g)" % (c["key"], c["w"], c["naturalW"]) for c in cs if c["w"] < c["naturalW"] - EPS]
    if narrow:
        out.append("%s: narrower than its natural width: %s" % (where, ", ".join(narrow)))
    short = [c["key"] for c in cs if c["h"] < one_h - EPS]
    if short:
        out.append("%s: shorter than the single row's %gpx: %s" % (where, one_h, ", ".join(short)))
    try:
        reserved = _px(row["mtabsH"])
        if abs(reserved - bar["offsetH"]) > EPS:
            out.append("%s: the panes' strip (--mtabs-h %s) is not the bar's height (%s)" % (where, row["mtabsH"], bar["offsetH"]))
    except AssertionError as e:
        out.append("%s: --mtabs-h unreadable: %s" % (where, e))
    if not row["pane"] or row["pane"]["bottom"] > bar["top"] + EPS:
        out.append("%s: the shown pane runs under the bar: %r against the bar's top %s" % (where, row["pane"], bar["top"]))
    out += _shape(where, row, "one" if row["natural"] <= vw + EPS else "two")
    return out


def _shape(where, row, rows):
    """The bar's shape: rows='one', the single row it is wherever its natural row fits, every control on it and the bar one
    control tall (the panes keep everything above that one row); rows='two', the fallback, the tabs filling the first row and
    the cluster together on the second at the right edge."""
    out = []
    vw, bar, cs = row["vw"], row["bar"], row["controls"]
    tabs = [c for c in cs if c["tab"]]
    acts = [c for c in cs if not c["tab"]]
    one_h = max((c["h"] for c in acts), default=0)
    if rows == "one":
        if row["natural"] > vw + EPS:
            out.append("%s: one row is owed here, yet the natural row (%gpx) is wider than the window" % (where, row["natural"]))
        if max(c["top"] for c in cs) - min(c["top"] for c in cs) > EPS:
            out.append("%s: one row is owed here, yet the controls are not on one row (tops %s)" % (
                where, ", ".join("%s %g" % (c["key"], c["top"]) for c in cs)))
        if abs(bar["offsetH"] - (one_h + bar["borderTop"] + bar["padBottom"])) > EPS:
            out.append("%s: one row is owed here, yet the bar is %spx tall, not one row of %gpx" % (where, bar["offsetH"], one_h))
    else:
        if row["natural"] <= vw + EPS:
            out.append("%s: the fallback is owed here, yet the natural row (%gpx) fits the window" % (where, row["natural"]))
        if tabs and max(c["top"] for c in tabs) - min(c["top"] for c in tabs) > EPS:
            out.append("%s: the tabs are not on one row" % where)
        if acts and max(c["top"] for c in acts) - min(c["top"] for c in acts) > EPS:
            out.append("%s: the action buttons are not on one row" % where)
        if tabs and acts and min(c["top"] for c in acts) < max(c["bottom"] for c in tabs) - EPS:
            out.append("%s: the natural row (%gpx) does not fit, yet the actions are not on a row under the tabs" % (where, row["natural"]))
        if acts and abs(acts[-1]["right"] - vw) > EPS:
            out.append("%s: the last action button does not sit at the right edge (%s)" % (where, acts[-1]["right"]))
        if any(abs(b["left"] - a["right"]) > EPS for a, b in zip(acts, acts[1:])):
            out.append("%s: the action buttons are not side by side" % where)
    return out


def _acts_problems(engine, acts):
    """The moved actions: each one click from the bar's Settings, doing what its bar button did, its glyph's state kept."""
    out = []
    where = "%s moved actions at %dx%d" % (engine, acts["vp"][0], acts["vp"][1])
    keys = [c["key"] for c in acts["bar"]["controls"] if not c["tab"]]
    if keys != list(BAR_ACTS):
        out.append("%s: the bar's actions are %s, not %s" % (where, keys, list(BAR_ACTS)))
    for act in MOVED:
        run = acts["runs"].get(act) or {}
        w = "%s, %s" % (where, act)
        card = run.get("card") or {}
        if not card.get("rowShown"):
            out.append("%s: the card's row of panel buttons is not shown on the phone" % w)
        btn = next((b for b in card.get("buttons", []) if b["act"] == act), None)
        if not btn:
            out.append("%s: no %s button in the card: %r" % (w, act, card.get("buttons")))
            continue
        c, vw, vh = card.get("card") or {}, acts["vp"][0], acts["vp"][1]
        if btn["left"] < -EPS or btn["right"] > vw + EPS or btn["top"] < -EPS or btn["bottom"] > vh + EPS:
            out.append("%s: the button is not wholly in the window: %r" % (w, btn))
        if not c or btn["left"] < c["left"] - EPS or btn["right"] > c["right"] + EPS or btn["top"] < c["top"] - EPS or btn["bottom"] > c["bottom"] + EPS:
            out.append("%s: the button is not wholly in the card: %r in %r" % (w, btn, c))
        if not btn["hit"]:
            out.append("%s: the element at the button's centre is not the button" % w)
        what = {"usage": "open the Usage modal", "net": "open the Remote kernels panel",
                "restart": "run the kernel's restart (the shell's handler taking the lab's refusal)"}[act]
        if not run.get("opened"):
            out.append("%s: one click on the card's button did not %s: %r" % (w, what, run.get("after")))
        # the restart's request: none before the click, exactly one after it, from the shell (the bar's handler's own POST)
        want_posts = ["shell"] if act == "restart" else []
        if run.get("restartsBefore") != [] or run.get("restarts") != want_posts:
            out.append("%s: POST /restart before the click %r and after it %r, not [] and %r" % (
                w, run.get("restartsBefore"), run.get("restarts"), want_posts))
        after = run.get("after") or {}
        if after.get("settingsOpen") or not run.get("cardHidden"):
            out.append("%s: the card is still open after the click: %r, card hidden %r" % (w, after, run.get("cardHidden")))
        if act != "net" and after.get("net"):
            out.append("%s: the click opened the Remote kernels panel" % w)
        if act != "usage" and after.get("usage"):
            out.append("%s: the click opened the Usage modal" % w)
    # the card's button vocabulary: each moved action wears Customize shortcuts' dress (#rs-keys-btn, the card's word button
    # the row's rules copy) at rest, its fill, hairline, radius, text, padding and press transition. The Remote kernels button
    # is read while the shell's poll lights it, and its text colour is the card's too: the accent goes on its glyph alone (PR
    # 976's round 1, ui-3; the glyph's colour is read on its svg below)
    dress = ((acts["runs"].get("usage") or {}).get("card") or {}).get("dress") or {}
    ref = dress.get("ref")
    if not ref:
        out.append("%s: no Customize shortcuts button to read the card's button dress from: %r" % (where, dress))
    else:
        got = {b["act"]: b for b in dress.get("acts", [])}
        for act in MOVED:
            b = got.get(act)
            if not b:
                continue   # its absence is listed above
            off = sorted(k for k in ref if b["dress"].get(k) != ref[k])
            if off:
                out.append("%s: the %s button does not wear the card's button dress: %s" % (
                    where, act, ", ".join("%s %r, not %r" % (k, b["dress"].get(k), ref[k]) for k in off)))
    # Usage with a reading (the lab's usage.json): enabled at the opening, its no-reading line not shown (and the click above
    # opened the Usage modal)
    u = ((acts["runs"].get("usage") or {}).get("card") or {}).get("usage")
    if not u or u.get("disabled") is not False or not u.get("line") or u["line"].get("shown") is not False:
        out.append("%s: with a reading, Usage is not enabled with its no-reading line hidden: %r" % (where, u))
    # the Remote kernels glyph in the card: at the first opening the state the shell's first poll painted on the rail (the
    # next poll held, so the card's paint is the opening's own); after the release the state of the second answer
    first, rel = (acts["runs"].get("usage") or {}).get("card", {}).get("glyph"), acts.get("released") or {}
    want = ["rn-me rn-ok", "rn-a rn-warn", "rn-b rn-ok"]
    rail = (acts["runs"].get("usage") or {}).get("rail") or {}
    if not first:
        out.append("%s: no Remote kernels glyph in the card" % where)
    else:
        if "on" not in (first["cls"] or "").split():
            out.append("%s: the card's Remote kernels glyph is not lit at the opening though a host is connected: %r" % (where, first))
        if [n and n["cls"] for n in first["nodes"]] != want:
            out.append("%s: the card's glyph nodes at the opening are %r, not %r" % (where, [n and n["cls"] for n in first["nodes"]], want))
        if [n and n["cls"] for n in rail.get("nodes", [])] != want:
            out.append("%s: the rail's glyph nodes are %r, not %r (the poll's premise)" % (where, [n and n["cls"] for n in rail.get("nodes", [])], want))
        if first["color"] != rail.get("color") or [n and n["fill"] for n in first["nodes"]] != [n and n["fill"] for n in rail.get("nodes", [])]:
            out.append("%s: the card's glyph does not wear the rail glyph's colours: %r against %r" % (where, first, rail))
    if rel.get("card") != ["rn-me rn-ok", "rn-a rn-ok", "rn-b rn-ok"]:
        out.append("%s: after the poll answered both hosts connected, the card's glyph nodes are %r" % (where, rel.get("card")))
    second = (acts["runs"].get("net") or {}).get("card", {}).get("glyph")
    if not second or [n and n["cls"] for n in second["nodes"]] != ["rn-me rn-ok", "rn-a rn-ok", "rn-b rn-ok"]:
        out.append("%s: at the second opening the card's glyph nodes are %r" % (where, second and [n and n["cls"] for n in second["nodes"]]))
    # the drop cue on the card's glyph: a drop that came while the card was closed plays no flash when the card next opens
    # (on the bar the flash played at the drop; a closed card shows nothing then, and the colours carry the state after it),
    # and a drop while the card is open flashes it
    drop = acts.get("drop") or {}
    if not drop.get("closedPolled"):
        out.append("%s: the poll that drops a host never reached the rail's glyph (the drop leg's premise): %r" % (where, drop))
    if not (drop.get("closed") or {}).get("cardHidden"):
        out.append("%s: the card was not closed when the host dropped (the drop leg's premise): %r" % (where, drop.get("closed")))
    re_ = drop.get("reopened")
    if not re_ or "rn-drop" in (re_["cls"] or "").split() or any(a.startswith("rs-pact-drop:") for a in (re_["anims"] or [])):
        out.append("%s: a host dropped while the card was closed, and the card's next opening plays its flash: %r" % (where, re_))
    if not drop.get("backUp"):
        out.append("%s: the host never came back on the rail's glyph before the second drop (its premise): %r" % (where, drop))
    live = drop.get("openDrop")
    if not live or "rs-pact-drop:running" not in (live["anims"] or []):
        out.append("%s: a host dropping while the card is open does not flash the card's glyph: %r" % (where, live))
    # the Token usage panel over the card (PR 976's round 1, fresh-1): it hides the card with no settings message, so a drop
    # while it is up must not flash the card's glyph when the panel closes and the card shows again
    ra = drop.get("analytics") or {}
    if not ra.get("backUp") or not ra.get("opened") or not ra.get("dropped") or not (ra.get("during") or {}).get("cardHidden"):
        out.append("%s: the Token usage panel leg's premise (the host back up, the panel opened over the card and hiding it, "
                   "the host dropping while it was up): %r" % (where, ra))
    ra_after = ra.get("after")
    if not ra.get("closed") or not ra_after or ra_after.get("cardHidden") or "rn-drop" in (ra_after["cls"] or "").split() \
            or any(a.startswith("rs-pact-drop:") for a in (ra_after["anims"] or [])):
        out.append("%s: a host dropped while the Token usage panel hid the card, and the card's glyph flashes when the panel "
                   "closes: %r" % (where, ra))
    return out


def _dashes(v):
    """A computed stroke-dasharray as its lengths, by value ('3px, 3px', '3, 3' and '3px 3px' alike); 'none' as []."""
    v = (v or "").strip()
    return [] if v in ("", "none") else [float(x) for x in re.findall(r"[\d.]+", v)]


def _states_problems(engine, acts):
    """The card glyph's marching and unlit states (PR 976's round 1, tests-2 and fresh-2): with the card open, a host attaching
    marks the card's copy busy beside the rail's and its connector dashes march (rs-pact-march running, dashes of 3 and 3),
    and the hosts settling take that off; no host up leaves the copy unlit with the card open, and at the card's next opening
    after a poll with no host came while it was closed."""
    out = []
    where = "%s the glyph's states at %dx%d" % (engine, acts["vp"][0], acts["vp"][1])
    st = acts.get("states") or {}
    cls = lambda s: set((s or "").split())
    att = st.get("attaching") or {}
    card = att.get("card") or {}
    if not st.get("attachPolled") or "busy" not in cls(att.get("rail")):
        out.append("%s: the attaching poll never marked the rail's glyph busy (the premise): %r" % (where, att))
    if card.get("cardHidden") is not False or not {"on", "busy"} <= cls(card.get("cls")):
        out.append("%s: a host attaching with the card open, and the card's glyph is not lit and busy as the rail's is: %r" % (where, att))
    if card.get("anim") != "rs-pact-march" or _dashes(card.get("dash")) != [3.0, 3.0] or "rs-pact-march:running" not in (card.get("runs") or []):
        out.append("%s: a host attaching with the card open, and the card glyph's connector dashes do not march "
                   "(rs-pact-march running over dashes of 3 and 3): %r" % (where, card))
    sett = st.get("settled") or {}
    sc = sett.get("card") or {}
    if not st.get("settledPolled") or "busy" in cls(sett.get("rail")):
        out.append("%s: the settled poll never took busy off the rail's glyph (the premise): %r" % (where, sett))
    if not sc or "busy" in cls(sc.get("cls")) or sc.get("anim") != "none" or any(x.startswith("rs-pact-march:") for x in (sc.get("runs") or [])):
        out.append("%s: the hosts settled, and the card's glyph still marches: %r" % (where, sc))
    none = st.get("noneOpen") or {}
    nc = none.get("card") or {}
    if not st.get("nonePolled") or "on" in cls(none.get("rail")):
        out.append("%s: the poll with no host never put the rail's glyph out (the premise): %r" % (where, none))
    if not nc or nc.get("cardHidden") is not False or "on" in cls(nc.get("cls")):
        out.append("%s: no host up with the card open, and the card's glyph is still lit: %r" % (where, none))
    if not st.get("backUp") or "on" not in cls((st.get("upBeforeClose") or {}).get("cls")) or not st.get("noneClosedPolled") \
            or (st.get("noneClosed") or {}).get("cardHidden") is not True:
        out.append("%s: the closed half's premise (the hosts back up and the card's glyph lit, then the card closed when the "
                   "poll with no host came): %r" % (where, st))
    # The closed-then-opened line has two redundant sites behind it, so it goes red only under the mutant of both (accepted by
    # romp-manager after PR 976's round 1). The poll paints the card's copy through mnet even while the card is closed
    # (paintIcon's toggle of 'on'), and the opening copies the rail icon's live 'on' onto it (the settings listener's toggle),
    # each taking 'on' off when no host is up. With the poll's toggle made add-only, the closed copy keeps 'on' and the
    # opening's copy, reading the rail icon, takes it off; with the opening's copy made add-only, the poll has already taken
    # it off while the card was closed. Each one-site mutant leaves the copy unlit at the opening, so each is equivalent on
    # this line; the open line above is the one red under the poll's alone
    reo = st.get("noneReopened") or {}
    rc = reo.get("card") or {}
    if not rc or rc.get("cardHidden") is not False or "on" in cls(rc.get("cls")) or "on" in cls(reo.get("rail")):
        out.append("%s: no host up came while the card was closed, and the card's glyph is lit at its next opening: %r" % (where, reo))
    return out


def _no_reading_problems(engine, nr):
    """Usage with no reading: disabled with its line once the opening's ask has ended, its name in the disabled button's own
    colour (the faint one, not the text colour gear.css sets on an enabled Usage's name), a tap leaving the card open and posting
    nothing; then a reading landing while the card is still open enables Usage there with no line (the shell tells the open
    card), the readings emptying disable it with its line again and filling enable it again; the readings emptying, and
    filling, while the Token usage panel stands over the card show in the card its close shows; and one click opens the Usage
    modal."""
    out = []
    where = "%s Usage with no reading at %dx%d" % (engine, nr["vp"][0], nr["vp"][1])
    pre = nr.get("premise") or {}
    if pre.get("pulls", 0) < 1 or pre.get("readout") != "":
        out.append("%s: the shell holds a reading before the card opens (the leg's premise): %r" % (where, pre))
    if not nr.get("firstAsked"):
        out.append("%s: the opening's ask for a fresh reading never ended (the romp loader still up): %r" % (where, nr.get("first")))
    first = nr.get("first")
    if not first or first.get("disabled") is not True or not first.get("line") or first["line"].get("shown") is not True \
            or first["line"].get("text") != USAGE_NONE:
        out.append("%s: Usage is not disabled with the line %r: %r" % (where, USAGE_NONE, first))
    # ...and its name wears the disabled button's own colour, the faint one: the card's text colour that gear.css sets on the
    # label skips a disabled Usage (romp-manager's ruling on PR 976's round 2 pass keeps the labels at their resting colour)
    elif not (first.get("name") or {}).get("color") or (first.get("name") or {}).get("color") != first.get("color"):
        out.append("%s: the disabled Usage's name wears %r, not the disabled button's own colour %r" % (
            where, (first.get("name") or {}).get("color"), first.get("color")))
    tap = nr.get("tapped") or {}
    if not tap.get("settingsOpen") or tap.get("cardHidden") is not False:
        out.append("%s: a tap on Usage closed the card: %r" % (where, tap))
    if tap.get("usage") or tap.get("acts") != []:
        out.append("%s: a tap on Usage reached the shell (the Usage modal %r, phoneAct %r)" % (where, tap.get("usage"), tap.get("acts")))
    after = nr.get("afterTap")
    if not after or not after.get("line") or after["line"].get("shown") is not True:
        out.append("%s: after the tap the line saying there is no reading yet is not shown: %r" % (where, after))
    # a script's clicks on the disabled Usage (romp-manager's ruling after PR 976's round 1): each reaches the row's handler in
    # every engine, and the handler's check of the disabled state is what keeps it from the shell
    roads = {d.get("road"): d for d in nr.get("dispatched") or []}
    for road in ("label", "button", "glyph"):
        d = roads.get(road) or {}
        if not d.get("ran") or d.get("disabled") is not True:
            out.append("%s: the script's click on Usage's %s was not dispatched on a disabled Usage (its premise): %r" % (where, road, d))
        elif not d.get("settingsOpen") or d.get("cardHidden") is not False or d.get("usage") or d.get("acts") != []:
            out.append("%s: a script's click on the disabled Usage's %s ran the row's handler (settings open %r, card hidden %r, "
                       "the Usage modal %r, phoneAct %r)" % (where, road, d.get("settingsOpen"), d.get("cardHidden"), d.get("usage"), d.get("acts")))
    if not nr.get("arrived"):
        out.append("%s: the reading never reached the shell's readout (the second half's premise)" % where)
    still = nr.get("stillOpen") or {}
    if not still.get("settingsOpen") or still.get("cardHidden") is not False:
        out.append("%s: the card was not open when the reading landed (the second half's premise): %r" % (where, still))
    second = nr.get("second")
    if not second or second.get("disabled") is not False or not second.get("line") or second["line"].get("shown") is not False:
        out.append("%s: a reading landed while the card was open, and the open card does not show Usage enabled without its line: %r" % (where, second))
    if not nr.get("emptiedReadout") or not nr.get("refilledReadout"):
        out.append("%s: the shell's readout did not follow the emptying and the refilling (their premise): %r, %r" % (
            where, nr.get("emptiedReadout"), nr.get("refilledReadout")))
    emptied = nr.get("emptied")
    if not emptied or emptied.get("disabled") is not True or not emptied.get("line") or emptied["line"].get("shown") is not True:
        out.append("%s: the readings emptied while the card was open, and the open card does not show Usage disabled with its line: %r" % (where, emptied))
    refilled = nr.get("refilled")
    if not refilled or refilled.get("disabled") is not False or not refilled.get("line") or refilled["line"].get("shown") is not False:
        out.append("%s: the readings filled again while the card was open, and the open card does not show Usage enabled without its line: %r" % (where, refilled))
    # the readings changing while the Token usage panel stands over the card (the check of PR 976's round 1 fixes): the panel
    # hides the card with no word to the shell, and the card its close shows must show Usage as the readings now are. Each
    # turn starts at an opening, which reads Usage afresh in any tree
    pn = nr.get("panel") or {}
    pick = lambda *ks: {k: pn.get(k) for k in ks}
    fs = pn.get("fullStart") or {}
    if not fs.get("asked") or (fs.get("usage") or {}).get("disabled") is not False or not pn.get("opened") \
            or not pn.get("emptiedReadout") or not pn.get("closed"):
        out.append("%s: the first panel turn's premise (an opening with the readings filled showing Usage enabled, the panel "
                   "opened over the card, the readout emptied while it was up, the panel closed): %r" % (
                       where, pick("fullStart", "opened", "emptiedReadout", "closed")))
    pe = pn.get("emptied")
    if not pe or pe.get("disabled") is not True or not pe.get("line") or pe["line"].get("shown") is not True:
        out.append("%s: the readings emptied while the Token usage panel stood over the card, and the card its close shows "
                   "does not show Usage disabled with its line: %r" % (where, pe))
    es = pn.get("emptyStart") or {}
    if not es.get("asked") or (es.get("usage") or {}).get("disabled") is not True or not pn.get("opened2") \
            or not pn.get("filledReadout") or not pn.get("closed2"):
        out.append("%s: the second panel turn's premise (an opening with no reading showing Usage disabled, the panel opened "
                   "over the card, the readout filled while it was up, the panel closed): %r" % (
                       where, pick("emptyStart", "opened2", "filledReadout", "closed2")))
    pf = pn.get("filled")
    if not pf or pf.get("disabled") is not False or not pf.get("line") or pf["line"].get("shown") is not False:
        out.append("%s: the readings filled while the Token usage panel stood over the card, and the card its close shows "
                   "does not show Usage enabled without its line: %r" % (where, pf))
    clicked = nr.get("clicked") or {}
    if not nr.get("opened") or clicked.get("settingsOpen") or clicked.get("cardHidden") is not True or clicked.get("acts") != ["usage"]:
        out.append("%s: with the reading, one click on Usage did not close the card and open the Usage modal: opened %r, %r" % (
            where, nr.get("opened"), clicked))
    return out


def _unpulled_problems(engine, up):
    """A reading the kernel holds and the shell has not pulled: the card's opening asks the shell for a fresh pull, shows the
    romp loader on Usage while it is in flight, in the name's place (the button disabled, no line, the name unseen, a tap on it
    reaching nothing), and once it ends shows Usage enabled with no line and its name seen; one click opens the Usage modal
    (PR 976's round 1, correctness-1 and extra6-1)."""
    out = []
    where = "%s Usage over an unpulled reading at %dx%d" % (engine, up["vp"][0], up["vp"][1])
    pre = up.get("premise") or {}
    if pre.get("boots", 0) < 1 or pre.get("readout") != "" or pre.get("sessionsLoaded") is not False:
        out.append("%s: the leg's premise (the boot pull answered no rows, the readout empty, the Sessions pane unloaded): %r" % (where, pre))
    if not up.get("asked"):
        out.append("%s: the card's opening asks the shell for no fresh reading (no pull under /usage/ after the opening)" % where)
    d = up.get("during")
    if not d or d.get("disabled") is not True or d.get("busy") != "true" or not d.get("line") or d["line"].get("shown") is not False \
            or not d.get("wait") or d["wait"].get("shown") is not True or d["wait"].get("text") != "romp" \
            or not {"fask-swirl-spin", "fileview-pulse"} <= set(d["wait"].get("anims") or []):
        out.append("%s: while the opening's pull is in flight, Usage does not show the romp loader (spinning, its dots pulsing), "
                   "disabled and busy, with no line: %r" % (where, d))
    # a tap on a disabled Usage reaches nothing: the browser dispatches no click for it (the row's handler, which returns on a
    # disabled button, is the second guard; a mutant that never disables Usage turns this line red)
    td = up.get("tappedDuring") or {}
    if not td.get("settingsOpen") or td.get("cardHidden") is not False or td.get("usage") or td.get("acts") != []:
        out.append("%s: a tap on Usage while the opening's pull is in flight closed the card or reached the shell: %r" % (where, td))
    if not up.get("ended") or not up.get("readout"):
        out.append("%s: the opening's pull did not land (the ask ended %r, the readout filled %r)" % (where, up.get("ended"), up.get("readout")))
    a = up.get("after")
    if not a or a.get("disabled") is not False or a.get("busy") is not None or not a.get("line") or a["line"].get("shown") is not False \
            or (a.get("wait") or {}).get("shown") is not False:
        out.append("%s: after the opening's pull, Usage is not enabled with no line and no loader: %r" % (where, a))
    # the loader shows in the name's place (romp-manager's decision on PR 976's round 1 builds): the name unseen while the pull
    # is in flight, and seen once it has ended
    if ((d or {}).get("name") or {}).get("shown") is not False:
        out.append("%s: while the opening's pull is in flight, Usage's name is seen, where the loader shows in its place: %r" % (
            where, (d or {}).get("name")))
    if ((a or {}).get("name") or {}).get("shown") is not True:
        out.append("%s: after the opening's pull, Usage's name is not seen: %r" % (where, (a or {}).get("name")))
    clicked = up.get("clicked") or {}
    if not up.get("opened") or clicked.get("settingsOpen") or clicked.get("cardHidden") is not True or clicked.get("acts") != ["usage"]:
        out.append("%s: one click on Usage did not close the card and open the Usage modal: opened %r, %r" % (where, up.get("opened"), clicked))
    return out


def _failed_problems(engine, fr):
    """The reads that fail (romp-manager's rulings after PR 976's round 1): with no reading in the shell, an opening's pull
    answered with an error status, one that fails in transit, and one the kernel never answers (ended by the pull's bound,
    set to HANG_MS on the shell here) each end with Usage disabled and the line USAGE_ERR, never USAGE_NONE, and the card
    open; after each of them, an opening whose pull the kernel answers ok with no rows shows Usage disabled with USAGE_NONE
    alone; in the reopen race, the card's earlier pull ending after the reopened card's pull (failed in transit, let through
    to the lab's reading, or answered with ERROR_STATUS) leaves the flag the later pull's and, failing, the readings as they
    were, while its ok answer still writes its reading (Usage enabled beside USAGE_ERR there), read in the card and again
    through its surface (PR 976's round 2); after an opening over ERROR_STATUS, a reading the timeline forwards to the shell
    shows Usage enabled with neither line (PR 976's round 2); a later opening whose pull reads the lab's reading shows Usage
    enabled with neither line; and then, with that reading cached, an opening whose pull fails in transit shows Usage enabled
    with USAGE_ERR beside its name, past the name's right edge, with the loader out of the layout (PR 976's round 2), one
    click opening the Usage modal; and, the shell holding a window reading of its own and the card's pull ended by its bound,
    a tap whose own pull is held opens the Usage modal within 1 s over that reading with its age, and the open modal follows
    the held pull's fresher answer with its By session button left in place (PR 976's round 2); and, the panel opened that way
    again and closed while the tap's pull is held, that pull's answer leaves it closed (PR 976's round 2); and, the panel
    opened that way again and left open, that pull answered with ERROR_STATUS, which empties the readings, closes it, the
    backdrop and the close hook with it (romp-manager's ruling on PR 976's round 2 pass)."""
    out = []
    where = "%s Usage over a failed read at %dx%d" % (engine, fr["vp"][0], fr["vp"][1])
    pre = fr.get("premise") or {}
    if pre.get("boots", 0) < 1 or pre.get("readout") != "":
        out.append("%s: the shell holds a reading before the card opens (the leg's premise): %r" % (where, pre))

    def not_failed(u):
        return (not u or u.get("disabled") is not True or not u.get("err") or u["err"].get("shown") is not True
                or u["err"].get("text") != USAGE_ERR or not u.get("line") or u["line"].get("shown") is not False)

    def card_closed(sh):
        return not sh.get("settingsOpen") or sh.get("cardHidden") is not False or sh.get("usage") or sh.get("acts") != []
    for key, what in (("status", "the kernel answered the opening's pull with an error status (%d)" % ERROR_STATUS),
                      ("transit", "the opening's pull failed in transit")):
        t = fr.get(key) or {}
        if not t.get("asked"):
            out.append("%s: %s, and the opening's ask never ended (the loader still up): %r" % (where, what, t.get("usage")))
        if not_failed(t.get("usage")):
            out.append("%s: %s, and Usage is not disabled with the line %r (and without %r): %r" % (where, what, USAGE_ERR, USAGE_NONE, t.get("usage")))
        if card_closed(t.get("shell") or {}):
            out.append("%s: %s, and the card closed or reached the shell: %r" % (where, what, t.get("shell")))
    hg = fr.get("hang") or {}
    d = hg.get("during")
    if not hg.get("held") or not d or d.get("disabled") is not True or not d.get("wait") or d["wait"].get("shown") is not True:
        out.append("%s: the hung pull's premise (the opening's pull held, Usage showing the romp loader): held %r, %r" % (where, hg.get("held"), d))
    if not hg.get("ended") or not HANG_MS <= (hg.get("elapsed") or 0) <= HANG_WAIT_MS:
        out.append("%s: the kernel never answered the opening's pull, and the loader did not end on the pull's bound (%d ms, set "
                   "on the shell) between %d and %d ms after the click: ended %r, %r ms after the click" % (
                       where, HANG_MS, HANG_MS, HANG_WAIT_MS, hg.get("ended"), hg.get("elapsed")))
    if not_failed(hg.get("after")):
        out.append("%s: the kernel never answered the opening's pull, and once the bound ended it Usage is not disabled with the "
                   "line %r (and without %r): %r" % (where, USAGE_ERR, USAGE_NONE, hg.get("after")))
    if card_closed(hg.get("shell") or {}):
        out.append("%s: the hung pull's card closed or reached the shell: %r" % (where, hg.get("shell")))

    def not_none(u):
        return (not u or u.get("disabled") is not True or not u.get("line") or u["line"].get("shown") is not True
                or u["line"].get("text") != USAGE_NONE or not u.get("err") or u["err"].get("shown") is not False)
    # after each failure, an opening whose pull the kernel answers ok with no rows: USAGE_NONE alone. So an ok answer clears the
    # failure, and the failure after it starts from a read that did not fail: the line each failure shows above is its own doing,
    # not a flag an earlier failure left set
    for key, after in (("okAfterStatus", "the error status"), ("okAfterTransit", "the failure in transit"),
                       ("okAfterHang", "the hung pull")):
        t = fr.get(key) or {}
        if not t.get("asked") or not_none(t.get("usage")):
            out.append("%s: after %s, an opening whose pull the kernel answered ok with no rows does not show Usage disabled with "
                       "the line %r alone (%r hidden): asked %r, %r" % (where, after, USAGE_NONE, USAGE_ERR, t.get("asked"), t.get("usage")))

    def not_enabled(u):
        return (not u or u.get("disabled") is not False or not u.get("line") or u["line"].get("shown") is not False
                or not u.get("err") or u["err"].get("shown") is not False)

    def not_enabled_failed(u):
        return (not u or u.get("disabled") is not False or not u.get("err") or u["err"].get("shown") is not True
                or u["err"].get("text") != USAGE_ERR or not u.get("line") or u["line"].get("shown") is not False)
    # the reopen race: the card's pull A held, the card reopened over pull B, B ended; then A ended after B (the order the
    # driver's wrapper over the shell's pull recorded). A read that ends after a later one has ended changes neither the flag
    # nor, with an error status, the readings, and its ok answer still writes the readings (romp-manager's decisions 5 and 6
    # on PR 976's round 1 builds): A failing in transit after B answered no rows leaves USAGE_NONE alone (the failed path's
    # check); A let through to the lab's reading after B failed in transit fills the readout and leaves Usage enabled beside
    # USAGE_ERR, B's failure kept (the answer's flag write, and the ok answer that still writes: PR 976's round 2, tests-1); A
    # answered with ERROR_STATUS after B reached the lab leaves Usage enabled with neither line (the error status's emptying of
    # the readings). Each is read once more through the card's own surface, the shell's layout word, with the shell's flag
    # (PR 976's round 2, tests-2): a late failure that wrote the flag and skipped only the card's tell would show there
    for key, a_end, b_end, what, b_wrong, b_state, a_wrong, a_state, flag in (
            ("raceTransit", "failed", "answered", "failed in transit", not_none, "disabled with the line %r alone" % USAGE_NONE,
             not_none, "disabled with the line %r alone" % USAGE_NONE, False),
            ("raceOk", "answered", "failed", "was let through to the lab's reading", not_failed,
             "disabled with the line %r alone" % USAGE_ERR, not_enabled_failed,
             "enabled beside the line %r, the later pull's failure kept and the held pull's reading written" % USAGE_ERR, True),
            ("raceStatus", "answered", "answered", "was answered with an error status (%d)" % ERROR_STATUS, not_enabled,
             "enabled with neither line", not_enabled, "enabled with neither line", False)):
        rc = fr.get(key) or {}
        p = rc.get("pulls") or []
        order = (len(p) >= 2 and p[0].get("end") == a_end and p[1].get("end") == b_end
                 and 0 < (p[1].get("at") or 0) < (p[0].get("at") or 0))
        if not rc.get("held") or not rc.get("bAsked") or not rc.get("aEnded") or not order or b_wrong(rc.get("afterB")):
            out.append("%s: the reopen race's premise (the card's pull held, the card reopened over a later pull whose answer "
                       "shows Usage %s, the held pull ending after it): held %r, the later ask ended %r, the held pull's end "
                       "run %r, the pulls' ends %r, Usage %r" % (where, b_state, rc.get("held"), rc.get("bAsked"), rc.get("aEnded"),
                                                                 p, rc.get("afterB")))
        if a_wrong(rc.get("afterA")):
            out.append("%s: the card's earlier pull %s after the reopened card's pull had ended, and Usage is not %s: %r"
                       % (where, what, a_state, rc.get("afterA")))
        if key == "raceOk" and rc.get("readout") is not True:
            out.append("%s: the card's earlier pull %s after the reopened card's pull had ended, and the shell's readout is not "
                       "filled: its ok answer wrote no reading (%r)" % (where, what, rc.get("readout")))
        if not rc.get("surfaceArrived"):
            out.append("%s: the shell's layout word and the probe after it never reached the card (the surface read's premise): %r"
                       % (where, rc.get("surfaceArrived")))
        elif a_wrong(rc.get("afterSurface")) or rc.get("flag") is not flag:
            out.append("%s: the card's earlier pull %s after the reopened card's pull had ended, and read again through the card's "
                       "surface (the shell's layout word) Usage is not %s, or the shell's flag is not %r: %r, flag %r"
                       % (where, what, a_state, flag, rc.get("afterSurface"), rc.get("flag")))
        if card_closed(rc.get("shell") or {}):
            out.append("%s: the reopen race's card closed or reached the shell: %r" % (where, rc.get("shell")))
    # the timeline's forward after a failed read (PR 976's round 2, tests-3): an opening over ERROR_STATUS (the readings emptied,
    # Usage disabled beside USAGE_ERR), the card left open, then the lab's reading posted as the timeline posts it: the readout
    # fills, and Usage is enabled with neither line, since the forward is a read that ended and clears the failure
    fw = fr.get("forward") or {}
    if not fw.get("asked") or not_failed(fw.get("before")):
        out.append("%s: the forward's premise (an opening over an error status, Usage disabled with the line %r): asked %r, %r" % (
            where, USAGE_ERR, fw.get("asked"), fw.get("before")))
    if not fw.get("filled"):
        out.append("%s: the lab's reading posted as the timeline posts it never filled the shell's readout (the forward's premise)" % where)
    if not_enabled(fw.get("after")):
        out.append("%s: after a failed read, a reading the timeline forwards does not show Usage enabled with neither line: %r" % (
            where, fw.get("after")))
    if card_closed(fw.get("shell") or {}):
        out.append("%s: the forward's card closed or reached the shell: %r" % (where, fw.get("shell")))
    lab = fr.get("lab") or {}
    u = lab.get("usage")
    if not lab.get("asked") or not u or u.get("disabled") is not False or (u.get("line") or {}).get("shown") is not False \
            or (u.get("err") or {"shown": False}).get("shown") is not False:
        out.append("%s: after the failures, an opening whose pull read the lab's reading does not show Usage enabled with "
                   "neither line: %r" % (where, lab))
    # a failed read over a cached reading (romp-manager's decision on PR 976's round 1 builds): the shell holds the lab's reading
    # and the opening's pull fails in transit, which leaves it, so Usage stays enabled with the line USAGE_ERR beside its name
    # (not USAGE_NONE), and one click opens the Usage modal over the reading the shell still holds
    cd = fr.get("cached") or {}
    cu = cd.get("usage")
    if not cd.get("asked") or cd.get("reading") is not True:
        out.append("%s: the cached reading's premise (the ask ended, the shell still holding a reading): asked %r, reading %r" % (
            where, cd.get("asked"), cd.get("reading")))
    if not cu or cu.get("disabled") is not False or not cu.get("err") or cu["err"].get("shown") is not True \
            or cu["err"].get("text") != USAGE_ERR or not cu.get("line") or cu["line"].get("shown") is not False:
        out.append("%s: the opening's pull failed in transit over a cached reading, and Usage is not enabled with the line %r "
                   "(and without %r): %r" % (where, USAGE_ERR, USAGE_NONE, cu))
    if ((cu or {}).get("name") or {}).get("shown") is not True:
        out.append("%s: the opening's pull failed in transit over a cached reading, and Usage's name is not seen beside the line "
                   "%r: %r" % (where, USAGE_ERR, (cu or {}).get("name")))
    # ...beside it, past its right edge, with the loader out of the layout while the line shows (PR 976's round 2, fresh-2)
    if cu and (cu.get("err") or {}).get("shown"):
        el, nr = (cu.get("err") or {}).get("left"), (cu.get("name") or {}).get("right")
        if not _num(el) or not _num(nr):
            out.append("%s: over a cached reading, the line's or the name's box unread (the line's left %r, the name's right %r)" % (where, el, nr))
        elif el < nr - SAME:
            out.append("%s: over a cached reading, the line %r overlaps Usage's name: its left edge %.2f, the name's right edge %.2f" % (
                where, USAGE_ERR, el, nr))
        if (cu.get("wait") or {}).get("display") != "none":
            out.append("%s: over a cached reading, the loader is laid out while the line %r shows (display %r)" % (
                where, USAGE_ERR, (cu.get("wait") or {}).get("display")))
    if card_closed(cd.get("shell") or {}):
        out.append("%s: the failed read over a cached reading closed the card or reached the shell before the click: %r" % (where, cd.get("shell")))
    ck = cd.get("clicked") or {}
    if not cd.get("opened") or ck.get("settingsOpen") or ck.get("cardHidden") is not True or ck.get("acts") != ["usage"]:
        out.append("%s: over a cached reading with the line %r, one click on Usage did not close the card and open the Usage "
                   "modal: opened %r, %r" % (where, USAGE_ERR, cd.get("opened"), ck))
    # the tap opens at once (PR 976's round 2, romp-manager's first rule): the shell holds a window reading of its own, the
    # card's pull is held past HANG_MS and ends on the bound (Usage enabled beside USAGE_ERR), and a tap whose own pull is held
    # opens the Usage modal within 1 s over that reading, its window section and its age line (updated 10m ago); the held pull
    # answered with a fresher reading of the same window (reported now), the open modal follows it (updated just now)
    at = fr.get("atOnce") or {}
    bt = at.get("barsTurn") or {}
    if not bt.get("asked") or not_enabled(bt.get("usage")) or not at.get("cardHeld") or not at.get("cardEnded") \
            or at.get("reading") is not True or not_enabled_failed(at.get("usage")):
        out.append("%s: the at-once tap's premise (a window reading in the shell showing Usage enabled, then the card's pull held "
                   "and ended by its bound, the reading kept, Usage enabled beside %r): %r" % (
                       where, USAGE_ERR, {k: at.get(k) for k in ("barsTurn", "cardHeld", "cardEnded", "reading", "usage")}))
    bf = at.get("before") or {}
    if not at.get("opened") or bf.get("up") is not True or bf.get("windows") is not True or "10m ago" not in (bf.get("age") or ""):
        out.append("%s: with the newest read failed over a cached reading, a tap on Usage whose own pull is held does not open the "
                   "Usage modal within 1 s over that reading with its age: opened %r (%r ms after the click), %r" % (
                       where, at.get("opened"), at.get("elapsed"), bf))
    ak = at.get("clicked") or {}
    if not at.get("tapHeld") or ak.get("settingsOpen") or ak.get("cardHidden") is not True or ak.get("acts") != ["usage"]:
        out.append("%s: the at-once tap did not close the card, post phoneAct usage and hold its own pull: held %r, %r" % (
            where, at.get("tapHeld"), ak))
    af = at.get("after") or {}
    if not at.get("followed") or af.get("up") is not True or "just now" not in (af.get("age") or ""):
        out.append("%s: the tap's held pull ended with a fresher reading, and the open Usage modal did not follow it: followed %r, "
                   "%r" % (where, at.get("followed"), af))
    # ...and the repaint left the modal's By session button in place, the same node (ui/CLAUDE.md: a button a re-render rebuilds
    # loses the click pressed on it, and the refresh can land during that press)
    if at.get("followed") and at.get("keptButton") is not True:
        out.append("%s: the open Usage modal's repaint replaced its By session button (a press on it as the refresh landed would be "
                   "lost): %r" % (where, at.get("keptButton")))
    # ...and the refresh behind that panel never opens the panel itself (PR 976's round 2, romp-manager's first rule): the card's
    # pull again ended by its bound over the reading, a tap whose own pull is held opens the modal within 1 s, the modal is
    # closed while that pull is held, and once the pull's fresher answer has run in the shell the modal is still closed, the
    # backdrop off
    cf = fr.get("closedFirst") or {}
    if not cf.get("cardHeld") or not cf.get("cardEnded") or cf.get("reading") is not True or not_enabled_failed(cf.get("usage")):
        out.append("%s: the closed panel's premise (the card's pull held and ended by its bound, the reading kept, Usage enabled "
                   "beside %r): %r" % (where, USAGE_ERR, {k: cf.get(k) for k in ("cardHeld", "cardEnded", "reading", "usage")}))
    ck = cf.get("clicked") or {}
    if not cf.get("opened") or not cf.get("tapHeld") or ck.get("settingsOpen") or ck.get("cardHidden") is not True \
            or ck.get("acts") != ["usage"]:
        out.append("%s: the closed panel's premise (a tap whose own pull is held, closing the card, posting phoneAct usage and "
                   "opening the Usage modal within 1 s): opened %r, held %r, %r" % (where, cf.get("opened"), cf.get("tapHeld"), ck))
    cl = cf.get("closed") or {}
    if cl.get("up") is not False or cl.get("backOn") is not False or cl.get("closeSet") is not False:
        out.append("%s: the closed panel's premise (the Usage modal closed while the tap's pull is held): %r" % (where, cl))
    ca = cf.get("after") or {}
    if not cf.get("answered"):
        out.append("%s: the tap's held pull was answered with a reading and the shell's flag never cleared (the answer never ran in "
                   "the shell, the closed panel's premise): %r" % (where, ca))
    elif ca.get("up") is not False or ca.get("backOn") is not False or ca.get("closeSet") is not False:
        out.append("%s: the Usage modal was closed while the tap's pull was held, and that pull's answer opened it again: %r" % (
            where, ca))
    # ...and a refresh behind that panel that empties the readings closes it (romp-manager's ruling on PR 976's round 2 pass):
    # the card's pull again ended by its bound over the reading, a tap whose own pull is held opens the modal within 1 s, that
    # pull is answered with ERROR_STATUS while the modal is open, and once the answer has emptied the shell's readings the modal
    # is closed: the tip neither shown nor a modal, the backdrop off (its class, and its computed display none), the close hook
    # cleared, and the backdrop not the element at the window's centre, so nothing is left dimmed
    em = fr.get("emptiedOpen") or {}
    if not em.get("cardHeld") or not em.get("cardEnded") or em.get("reading") is not True or not_enabled_failed(em.get("usage")):
        out.append("%s: the emptying refresh's premise (the card's pull held and ended by its bound, the reading kept, Usage "
                   "enabled beside %r): %r" % (where, USAGE_ERR, {k: em.get(k) for k in ("cardHeld", "cardEnded", "reading", "usage")}))
    ek, eb = em.get("clicked") or {}, em.get("before") or {}
    if not em.get("opened") or not em.get("tapHeld") or ek.get("settingsOpen") or ek.get("cardHidden") is not True \
            or ek.get("acts") != ["usage"] or eb.get("up") is not True or eb.get("closeSet") is not True:
        out.append("%s: the emptying refresh's premise (a tap whose own pull is held, closing the card, posting phoneAct usage and "
                   "opening the Usage modal within 1 s, its close hook set): opened %r, held %r, %r, %r" % (
                       where, em.get("opened"), em.get("tapHeld"), ek, eb))
    ea = em.get("after") or {}
    if not em.get("emptied"):
        out.append("%s: the tap's held pull was answered with %d and the shell's readings never emptied (the answer never ran in "
                   "the shell, the emptying refresh's premise): %r" % (where, ERROR_STATUS, ea))
    elif ea.get("up") is not False or ea.get("tipShown") is not False or ea.get("tipModal") is not False \
            or ea.get("backOn") is not False or ea.get("backDisplay") != "none" or ea.get("closeSet") is not False \
            or ea.get("centre") in (None, "ru-back") or ea.get("settingsOpen") is not False:
        out.append("%s: the tap's held pull was answered with %d while the Usage modal was open, emptying the readings, and the "
                   "modal was not closed (the backdrop off, the close hook cleared, nothing left dimmed): %r" % (
                       where, ERROR_STATUS, ea))
    return out


def _height_problems(engine, contrast):
    """Loading to a reading, the common path, moves neither the row nor the tabs under it, at every phone width (romp-manager's
    decision on PR 976's round 1 builds: hold the loader's width): in the dark and the light theme, at each of HEIGHT_WIDTHS,
    the opening's pull held (the loader up) and then let through to the lab's reading (Usage enabled) give the row the same
    height, Usage the same box, and the tabs the same offset in the card and the same top in the window, compared to SAME px;
    and in both states Usage is one line, as tall as Restart kernel (a one-line button of the same dress, on another line of
    the row at these widths, so the row's stretch cannot make the two equal), and as wide as the loader: its words as wide as
    the loader's laid-out box, and Usage as wide as its glyph and those words with its gap, side padding and borders, so
    nothing else widens it. So the row is no taller for Usage than its name or the loader makes it. In both states, too, Usage
    is narrower than with No reading yet or Couldn't load, the widest states, whose width the decision turned down; those two
    are read at the same widths and otherwise not compared: the line beside the name widens Usage, which can wrap the row onto
    one more line on a narrow window (the module's docstring gives the widths). And the loader shows in the name's place: the
    name unseen while loading, and seen with a reading and beside either line. And each line sits beside the name, its left
    edge at or past the name's right edge, with the loader out of the layout (its computed display none) while it shows
    (PR 976's round 2, fresh-2)."""
    out = []
    num = lambda v: isinstance(v, (int, float)) and not isinstance(v, bool)
    for name, theme in THEMES:
        where = "%s the row and the tabs, %s theme (%s)" % (engine, name, theme)
        hs = (contrast.get(name) or {}).get("heights") or {}
        flags = {k: hs.get(k) for k in ("held", "readingEnded", "noneEnded", "failedEnded")}
        if not all(flags.values()):
            out.append("%s: the states' premise (the opening's pull held, then each later ask ended): %r" % (where, flags))
        st = {k: hs.get(k) or [] for k in ("loading", "reading", "none", "failed")}
        for k, rows in st.items():
            if [r.get("w") for r in rows] != list(HEIGHT_WIDTHS) or any(r.get("vw") != r.get("w") or not r.get("rowShown") for r in rows):
                out.append("%s: %s was not read with the row shown at each of %s: %r" % (
                    where, k, list(HEIGHT_WIDTHS), [(r.get("w"), r.get("vw"), r.get("rowShown")) for r in rows]))
        for i, w in enumerate(HEIGHT_WIDTHS):
            ld, rd, no, fl = (st[k][i] if i < len(st[k]) else {} for k in ("loading", "reading", "none", "failed"))
            if ld.get("wait") is not True or ld.get("disabled") is not True:
                out.append("%s at %dpx: the loading state's premise (the loader up, Usage disabled): %r" % (where, w, ld))
            if rd.get("disabled") is not False or rd.get("wait") or rd.get("none") or rd.get("err"):
                out.append("%s at %dpx: the reading state's premise (Usage enabled with no loader and neither line): %r" % (where, w, rd))
            if no.get("none") is not True:
                out.append("%s at %dpx: the no-reading state's premise (the line %r): %r" % (where, w, USAGE_NONE, no))
            if fl.get("err") is not True:
                out.append("%s at %dpx: the failed state's premise (the line %r): %r" % (where, w, USAGE_ERR, fl))
            for k, what in (("rowH", "the row's height"), ("usageW", "Usage's width"), ("usageH", "Usage's height"),
                            ("tabsAt", "the tabs' offset in the card"), ("tabsTop", "the tabs' top in the window")):
                a, b = ld.get(k), rd.get(k)
                if not num(a) or not num(b):
                    out.append("%s at %dpx: %s unread (loading %r, reading %r)" % (where, w, what, a, b))
                elif abs(a - b) > SAME:
                    out.append("%s at %dpx: %s changes from loading to a reading: %.2f, then %.2f" % (where, w, what, a, b))
            for s, r in (("loading", ld), ("a reading", rd)):
                if not all(num(r.get(k)) for k in ("usageH", "usageTop", "restartH", "restartTop")):
                    out.append("%s at %dpx: Usage's or Restart kernel's box unread with %s: %r" % (where, w, s, r))
                elif abs(r["usageTop"] - r["restartTop"]) <= SAME:
                    out.append("%s at %dpx: with %s Restart kernel shares Usage's line, where the row's stretch evens their heights "
                               "(the comparison's premise): %r" % (where, w, s, r))
                elif abs(r["usageH"] - r["restartH"]) > SAME:
                    out.append("%s at %dpx: with %s Usage is %.2f px tall where Restart kernel is %.2f: the row is taller for Usage" % (
                        where, w, s, r["usageH"], r["restartH"]))
            # ...and as wide as the loader, not the widest state (the same decision): loading and with a reading, Usage's words are
            # as wide as the loader's laid-out box, and Usage as wide as its glyph and those words with the gap between them, its
            # side padding and its borders, so nothing else widens it; and it is narrower than with either line. The two equalities
            # pin the width the decision chose; the third, the one it turned down
            for s, r in (("loading", ld), ("a reading", rd)):
                tw, lw, pt = r.get("txtW"), r.get("waitW"), r.get("parts") or {}
                kids = pt.get("kids") if isinstance(pt.get("kids"), list) else []
                if not num(tw) or not num(lw):
                    out.append("%s at %dpx: with %s Usage's words or the loader's laid-out box unread (words %r, loader %r)" % (
                        where, w, s, tw, lw))
                elif abs(tw - lw) > SAME:
                    out.append("%s at %dpx: with %s Usage's words are %.2f px wide where the loader is %.2f: Usage does not hold the "
                               "loader's width" % (where, w, s, tw, lw))
                if not kids or not all(num(x) for x in kids) or not all(num(pt.get(k)) for k in ("gap", "pad", "border")) \
                        or not num(r.get("usageW")):
                    out.append("%s at %dpx: Usage's parts unread with %s: %r" % (where, w, s, r))
                else:
                    fit = sum(kids) + pt["gap"] * (len(kids) - 1) + pt["pad"] + pt["border"]
                    if abs(r["usageW"] - fit) > SAME:
                        out.append("%s at %dpx: with %s Usage is %.2f px wide where its glyph and words with its gap, padding and "
                                   "borders come to %.2f: something else widens it" % (where, w, s, r["usageW"], fit))
                for line, o in ((USAGE_NONE, no), (USAGE_ERR, fl)):
                    if not num(r.get("usageW")) or not num(o.get("usageW")):
                        out.append("%s at %dpx: Usage's width unread with %s or with the line %r (%r, %r)" % (
                            where, w, s, line, r.get("usageW"), o.get("usageW")))
                    elif r["usageW"] >= o["usageW"] - SAME:
                        out.append("%s at %dpx: with %s Usage is %.2f px wide, no narrower than with the line %r (%.2f): it holds the "
                                   "widest state's width, not the loader's" % (where, w, s, r["usageW"], line, o["usageW"]))
            # ...and each line beside the name, its left edge at or past the name's right edge, with the loader out of the
            # layout while it shows (PR 976's round 2, fresh-2: without the line's own grid cell it lay over the name, and
            # with the loader laid out unseen Usage was wider by the loader's extra width)
            for line, o in ((USAGE_NONE, no), (USAGE_ERR, fl)):
                ll, nr = o.get("lineLeft"), (o.get("name") or {}).get("right")
                if not num(ll) or not num(nr):
                    out.append("%s at %dpx: with the line %r its left edge or the name's right edge unread (%r, %r)" % (where, w, line, ll, nr))
                elif ll < nr - SAME:
                    out.append("%s at %dpx: the line %r overlaps Usage's name: its left edge %.2f, the name's right edge %.2f" % (
                        where, w, line, ll, nr))
                if o.get("waitDisplay") != "none":
                    out.append("%s at %dpx: with the line %r the loader is laid out (display %r), where it leaves the layout while "
                               "a line shows" % (where, w, line, o.get("waitDisplay")))
            # ...and the loader shows in the name's place: the name unseen while it shows, and seen with a reading and beside
            # either line (its computed visibility and display, and a box)
            for s, r, seen in (("loading", ld, False), ("a reading", rd, True), ("the line %r" % USAGE_NONE, no, True),
                               ("the line %r" % USAGE_ERR, fl, True)):
                nm = r.get("name")
                if not isinstance(nm, dict) or nm.get("shown") is not seen:
                    out.append("%s at %dpx: with %s Usage's name is %s: %r" % (
                        where, w, s, "seen, where the loader shows in its place" if not seen else "not seen", nm))
    return out


def _skew_problems(engine, sk):
    """The deploy skew (PR 976's round 1, kernel-1): the shell publishes its marker beside the phoneAct listener, the card shows
    its row where the marker is and not where it is missing (a shell from before the move, with the phone layout and the three
    still on its bar), and a shell that cannot be asked for a reading leaves Usage as its bar button was, enabled with no line."""
    out = []
    where = "%s deploy skew at %dx%d" % (engine, sk["vp"][0], sk["vp"][1])
    if sk.get("marker") is not True:
        out.append("%s: the shell publishes no marker beside its phoneAct listener (window.__rompPhoneActs %r)" % (where, sk.get("marker")))
    head = sk.get("head") or {}
    if not head.get("rowShown"):
        out.append("%s: with the shell's marker, the card's row of moved actions is not shown: %r" % (where, head))
    older = sk.get("older") or {}
    if older.get("rowShown") is not False or any(w > 0 or h > 0 for w, h in older.get("boxes", [])):
        out.append("%s: with the phone layout and no marker (a shell from before the move), the card shows the row: %r" % (where, older))
    ca = sk.get("cannotAsk") or {}
    u = ca.get("usage")
    if not ca.get("rowShown") or not u or u.get("disabled") is not False or not u.get("line") or u["line"].get("shown") is not False:
        out.append("%s: where the shell cannot be asked for a reading, Usage is not enabled with no line, as its bar button was: %r" % (where, ca))
    # the layout word's source (romp-manager's ruling after PR 976's round 1): the card's link listener acts on the word from the
    # shell's own window alone. With the marker deleted, a word it acts on hides the row
    ln = sk.get("link") or {}
    if not ln.get("start") or not ln.get("selfArrived") or not ln.get("chatFrame") or not ln.get("paneArrived"):
        out.append("%s: the layout word leg's premise (the card open with its row, both probe words delivered, a chat pane to post "
                   "from): %r" % (where, ln))
    if ln.get("self") is not True:
        out.append("%s: a layout word posted from the settings frame's own window moved the card's row: %r" % (where, ln))
    if ln.get("pane") is not True:
        out.append("%s: a layout word posted from the chat pane's window moved the card's row: %r" % (where, ln))
    if not ln.get("parentHid") or not ln.get("parentShowed"):
        out.append("%s: the layout word from the shell's own window did not move the card's row (the control): hid %r, showed %r" % (
            where, ln.get("parentHid"), ln.get("parentShowed")))
    return out


def _follow_problems(engine, fl):
    """The row follows the layout while the card is open (PR 976's round 1, correctness-2 and ui-1): opened on the phone layout
    with its row, the window widened past 820px hides the row in the open card, and narrowed back shows it again; the row shown
    again carries no flash for a drop that came while it was hidden, and Usage's state is asked afresh (the lab's reading:
    enabled, no line); and the window crossing 820px either way while the Token usage panel stands over the card leaves the
    card its close shows with the row the layout calls for."""
    out = []
    where = "%s the row following the layout, %dx%d and %dx%d" % (engine, fl["vp"][0], fl["vp"][1], (fl.get("wide") or WIDE)[0], (fl.get("wide") or WIDE)[1])
    ph = fl.get("phone") or {}
    if ph.get("mobile") is not True or not ph.get("open") or not ph.get("rowShown"):
        out.append("%s: the leg's premise (the card open on the phone layout with its row shown): %r" % (where, ph))
    wr = fl.get("wideRow") or {}
    if wr.get("mobile") is not False or not wr.get("open"):
        out.append("%s: the widened window's premise (the desktop layout, the card still open): %r" % (where, wr))
    if not fl.get("hid") or wr.get("rowShown") is not False or any(w > 0 or h > 0 for w, h in wr.get("boxes", [])):
        out.append("%s: the window widened past the phone layout with the card open, and the row stays shown: %r" % (where, wr))
    if not fl.get("dropped") or "rn-drop" not in (fl.get("dropCls") or "").split():
        out.append("%s: the drop's premise (the host dropping on the rail's glyph while the window was wide, its class left on the "
                   "card's hidden glyph): dropped %r, the glyph's class %r" % (where, fl.get("dropped"), fl.get("dropCls")))
    nr = fl.get("narrowRow") or {}
    if nr.get("mobile") is not True or not nr.get("open"):
        out.append("%s: the narrowed window's premise (the phone layout, the card still open): %r" % (where, nr))
    if not fl.get("showed") or not nr.get("rowShown"):
        out.append("%s: the window narrowed to the phone layout with the card open, and the row stays hidden: %r" % (where, nr))
    g = fl.get("glyph")
    if not g or "rn-drop" in (g["cls"] or "").split() or any(a.startswith("rs-pact-drop:") for a in (g["anims"] or [])):
        out.append("%s: a host dropped while the row was hidden, and the row shown again flashes its glyph: %r" % (where, g))
    u = fl.get("usage")
    if not fl.get("asked") or not u or u.get("disabled") is not False or not u.get("line") or u["line"].get("shown") is not False:
        out.append("%s: the row shown again does not show Usage enabled with no line once its ask has ended (the lab's reading): %r" % (where, u))
    # the same turns with the Token usage panel over the card (the check of PR 976's round 1 fixes): the panel hides the card
    # with no word to the shell, and the card its close shows must have the row the layout now calls for. The second turn
    # starts at an opening on the desktop layout, which reads the layout in any tree
    pn = fl.get("panel") or {}
    pick = lambda *ks: {k: pn.get(k) for k in ks}
    st, wu = pn.get("start") or {}, pn.get("wideUnder") or {}
    if st.get("mobile") is not True or not st.get("rowShown") or not pn.get("opened") or not pn.get("wideTurned") \
            or wu.get("panel") is not True or wu.get("cardHidden") is not True or not pn.get("closed"):
        out.append("%s: the first panel turn's premise (the row shown on the phone layout, the panel opened over the card, the "
                   "window widened to the desktop layout while it was up, the panel closed): %r" % (
                       where, pick("start", "opened", "wideTurned", "wideUnder", "closed")))
    pw = pn.get("wideRow") or {}
    if not pn.get("hid") or pw.get("open") is not True or pw.get("rowShown") is not False or any(w > 0 or h > 0 for w, h in pw.get("boxes", [])):
        out.append("%s: the window widened past the phone layout while the Token usage panel stood over the card, and the card "
                   "its close shows still shows the row: %r" % (where, pw))
    wo, nu = pn.get("wideOpened") or {}, pn.get("narrowUnder") or {}
    if wo.get("mobile") is not False or wo.get("open") is not True or wo.get("rowShown") is not False or not pn.get("opened2") \
            or not pn.get("narrowTurned") or nu.get("panel") is not True or nu.get("cardHidden") is not True or not pn.get("closed2"):
        out.append("%s: the second panel turn's premise (the card opened on the desktop layout with no row, the panel opened "
                   "over it, the window narrowed to the phone layout while it was up, the panel closed): %r" % (
                       where, pick("wideOpened", "opened2", "narrowTurned", "narrowUnder", "closed2")))
    pr = pn.get("narrowRow") or {}
    if not pn.get("showed") or pr.get("mobile") is not True or pr.get("open") is not True or not pr.get("rowShown"):
        out.append("%s: the window narrowed to the phone layout while the Token usage panel stood over the card, and the card "
                   "its close shows has no row: %r" % (where, pr))
    pu = pn.get("usage")
    if not pn.get("asked") or not pu or pu.get("disabled") is not False or pu.get("busy") is not None or not pu.get("line") \
            or pu["line"].get("shown") is not False:
        out.append("%s: the row the narrowing showed under the Token usage panel does not show Usage enabled with no line once "
                   "its ask has ended (the lab's reading): %r" % (where, pu))
    return out


def _rail_problems(engine, rail):
    """The desktop rail equals af7d18250's at each width (RAIL_AF7), every action on screen and hit at its centre."""
    out = []
    for r in rail:
        w, h = r["vp"]
        where = "%s desktop rail %dx%d" % (engine, w, h)
        want = RAIL_AF7
        if r["mobile"] is not False:
            out.append("%s: the window is on the phone layout: %r" % (where, r))
        ids = [a["id"] for a in r["acts"]]
        if ids != [a["id"] for a in want]:
            out.append("%s: the rail's actions are %s, not af7d18250's %s" % (where, ids, [a["id"] for a in want]))
            continue
        # the settings card opened from the rail's gear: the phone's row of moved actions is not displayed (the rail has its own)
        card = (r.get("card") or {}).get("card")
        if not (r.get("card") or {}).get("opened") or not card or not card.get("row"):
            out.append("%s: the settings card did not open from the rail's gear with its row in it: %r" % (where, r.get("card")))
        elif card.get("display") != "none" or any(w > 0 or h > 0 for w, h in card.get("boxes", [])):
            out.append("%s: the settings card shows the phone's row of moved actions on the desktop: %r" % (where, card))
        vw, gear = r["vw"], r["acts"][-1]
        for a, b in zip(r["acts"], want):
            if a["left"] < -EPS or a["right"] > vw + EPS or not a["hit"]:
                out.append("%s: %s is not wholly on screen and hit at its centre: %r" % (where, a["id"], a))
            got = {"top": a["top"], "h": a["h"]}
            if a is gear:
                got["right"] = round(a["right"] - vw, 2)
            else:
                got.update(w=a["w"], left=round(a["left"] - gear["left"], 2), right=round(a["right"] - gear["left"], 2))
            for k, v in got.items():
                if abs(v - b[k]) > EPS:
                    out.append("%s: %s %s is %g, af7d18250's %g" % (where, a["id"], k, v, b[k]))
    return out


def _rgba(v):
    """A computed colour, 'rgb(r, g, b)' or 'rgba(r, g, b, a)' (commas or the spaced form), -> (r, g, b, a); anything else is a
    failure, not a guess."""
    m = re.fullmatch(r"rgba?\(\s*([\d.]+)[\s,]+([\d.]+)[\s,]+([\d.]+)(?:\s*[,/]\s*([\d.]+)(%?))?\s*\)", (v or "").strip())
    assert m, "not an rgb() colour: %r" % (v,)
    a = 1.0 if m.group(4) is None else float(m.group(4)) / (100.0 if m.group(5) else 1.0)
    return (float(m.group(1)), float(m.group(2)), float(m.group(3)), a)


def _over(fg, bg):
    """fg composited over the opaque bg."""
    return tuple(fg[i] * fg[3] + bg[i] * (1 - fg[3]) for i in range(3)) + (1.0,)


def _contrast(a, b):
    """WCAG's contrast ratio of two opaque colours."""
    def lum(c):
        ch = [x / 255.0 for x in c[:3]]
        ch = [x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4 for x in ch]
        return 0.2126 * ch[0] + 0.7152 * ch[1] + 0.0722 * ch[2]
    x, y = lum(a), lum(b)
    return (max(x, y) + 0.05) / (min(x, y) + 0.05)


def _hex(c):
    return "#" + "".join("%02x" % int(round(x)) for x in c[:3])


def _oklab_distance(a, b):
    """The Euclidean distance between two opaque sRGB colours in OKLab (Ottosson's matrices), x100."""
    def lab(c):
        r, g, bl = [x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in (v / 255.0 for v in c[:3])]
        lms = (0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * bl,
               0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * bl,
               0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * bl)
        l_, m_, s_ = [v ** (1.0 / 3.0) for v in lms]
        return (0.2104542553 * l_ + 0.7936177850 * m_ - 0.0040720468 * s_,
                1.9779984951 * l_ - 2.4285922050 * m_ + 0.4505937099 * s_,
                0.0259040371 * l_ + 0.7827717662 * m_ - 0.8086757660 * s_)
    return 100.0 * sum((p - q) ** 2 for p, q in zip(lab(a), lab(b))) ** 0.5


def _contrast_problems(engine, contrast):
    """Each colour the Remote kernels glyph wears reads at GLYPH_FLOOR or more against the card's background and against the
    button's own fill (the glyph sits on the button), at rest and with the pointer on the button (PR 976's round 1,
    extra6-2: the hovered fill is a fill the glyph sits on too), in the dark and the light theme; and the needs-you red stays
    SEPARATION_FLOOR or more from the connected node's colour in OKLab. The unlit glyph wears the same colour hovered as at
    rest (PR 976's round 2, ui-1), and Usage's Couldn't load line reads TEXT_FLOOR or more on the fill Usage wears hovered
    (romp-manager's first decision before round 2). Each of the two buttons' labels, the Remote kernels label and Usage's
    name, wears the same colour hovered as at rest and reads TEXT_FLOOR or more on the fill its button wears hovered
    (romp-manager's ruling on round 2's pass), in both themes."""
    out = []

    def label_problems(lwhere, rest, hov, hfill):
        # one label hovered: its colour as at rest, and TEXT_FLOOR or more on the hovered fill (both read, so a red names each)
        got = []
        if not rest or hov != rest:
            got.append("%s: its colour hovered, %r, is not its colour at rest, %r" % (lwhere, hov, rest))
        if hov:
            col = _over(_rgba(hov), hfill)
            ratio = _contrast(col, hfill)
            if ratio < TEXT_FLOOR:
                got.append("%s: hovered, it reads %.2f:1 (%s) on the hovered fill (%s), under %g:1" % (
                    lwhere, ratio, _hex(col), _hex(hfill), TEXT_FLOOR))
        else:
            got.append("%s: its colour hovered is unread" % lwhere)
        return got
    for name, theme in THEMES:
        where = "%s Remote kernels glyph, %s theme (%s)" % (engine, name, theme)
        t = contrast.get(name)
        if not t:
            out.append("%s: not read" % where)
            continue
        if t.get("light") is not (name == "light"):
            out.append("%s: the settings document's theme-light class is %r (the leg's premise)" % (where, t.get("light")))
        if not t.get("rowShown"):
            out.append("%s: the card's row of moved actions is not shown (the leg's premise)" % where)
        try:
            card = _rgba(t.get("card"))
            if card[3] != 1:
                out.append("%s: the card's background is not opaque (%r), so what lies under it is unmeasured" % (where, t.get("card")))
                continue
            fill = _over(_rgba(t.get("fill")), card)
            for k in GLYPH:
                col = _rgba((t.get("colours") or {}).get(k))
                on_card, on_fill = _contrast(_over(col, card), card), _contrast(_over(col, fill), fill)
                if on_card < GLYPH_FLOOR or on_fill < GLYPH_FLOOR:
                    out.append("%s: %s, %s, reads %.2f:1 on the card (%s) and %.2f:1 on the button's fill (%s), under %g:1" % (
                        where, k, _hex(_over(col, fill)), on_card, _hex(card), on_fill, _hex(fill), GLYPH_FLOOR))
            ok, warn = (_over(_rgba((t.get("colours") or {}).get(k)), fill) for k in ("connected", "needs you"))
            apart = _oklab_distance(ok, warn)
            if apart < SEPARATION_FLOOR:
                out.append("%s: the needs-you red %s is %.2f from the connected node's %s (OKLab distance x100), under %g" % (
                    where, _hex(warn), apart, _hex(ok), SEPARATION_FLOOR))
            hv = t.get("hover") or {}
            if hv.get("hovered") is not True:
                out.append("%s: the pointer on the Remote kernels button does not hover it (the hovered fill's premise): %r" % (where, hv))
            else:
                hfill = _over(_rgba(hv.get("fill")), card)
                for k in GLYPH:
                    col = _rgba((hv.get("colours") or {}).get(k))
                    on_hover = _contrast(_over(col, hfill), hfill)
                    if on_hover < GLYPH_FLOOR:
                        out.append("%s: %s, %s, reads %.2f:1 on the hovered button's fill (%s), under %g:1" % (
                            where, k, _hex(_over(col, hfill)), on_hover, _hex(hfill), GLYPH_FLOOR))
                # the unlit glyph keeps its own colour on hover (PR 976's round 2, ui-1): the button's hover colour, the accent,
                # does not reach it, so hover never makes an unlit glyph look lit
                rest_u, hov_u = (t.get("colours") or {}).get("unlit"), (hv.get("colours") or {}).get("unlit")
                if not rest_u or hov_u != rest_u:
                    out.append("%s: the unlit glyph's colour hovered, %r, is not its colour at rest, %r" % (where, hov_u, rest_u))
                # ...and the button's label keeps its resting colour on hover too, the card's text colour, which reads TEXT_FLOOR or
                # more on the hovered fill (romp-manager's ruling on PR 976's round 2 pass: the row's hover colour, the accent, read
                # under it there in the light theme)
                out += label_problems("%s Remote kernels label, %s theme (%s)" % (engine, name, theme), t.get("label"), hv.get("label"), hfill)
            # Usage hovered beside its Couldn't load line (romp-manager's first decision before PR 976's round 2): the line reads
            # TEXT_FLOOR or more on the fill Usage wears hovered, which is its resting fill
            uh, uwhere = t.get("usageHover") or {}, "%s Usage hovered, %s theme (%s)" % (engine, name, theme)
            if not uh.get("labEnded") or not uh.get("failedEnded") or uh.get("disabled") is not False or uh.get("errShown") is not True \
                    or uh.get("hovered") is not True or uh.get("restHovered") is not False:
                out.append("%s: the premise (an opening over the lab's reading, then one over a pull failed in transit showing Usage "
                           "enabled beside %r, the pointer off it for the resting read and on it holding :hover): %r" % (uwhere, USAGE_ERR, uh))
            else:
                ucard = _rgba(uh.get("card"))
                ufill = _over(_rgba(uh.get("fill")), ucard)
                uline = _over(_rgba(uh.get("line")), ufill)
                ratio = _contrast(uline, ufill)
                if ratio < TEXT_FLOOR:
                    out.append("%s: its line %r (%s) reads %.2f:1 on Usage's hovered fill (%s), under %g:1" % (
                        uwhere, USAGE_ERR, _hex(uline), ratio, _hex(ufill), TEXT_FLOOR))
                # ...and its name, its label, keeps its resting colour on hover, TEXT_FLOOR or more on that fill (romp-manager's
                # ruling on PR 976's round 2 pass)
                out += label_problems("%s Usage's name, %s theme (%s)" % (engine, name, theme), uh.get("nameRest"), uh.get("name"), ufill)
        except AssertionError as e:
            out.append("%s: unreadable: %s" % (where, e))
    return out


def _through(fg, under):
    """The pixel the colour fg paints, or with fg None the pixel beside it, through `under`, the driver's layers from fg's own
    element out to the first opaque background (each its background, background image and opacity) and the opacity of
    everything above that one: each element's background over what lies under it, then its content (the next element in, or fg
    at the innermost), then its opacity on the whole group, as normal blending composites. An AssertionError where the layers
    cannot be measured: no opaque background, a background image, an opacity on or above the opaque one, a colour not rgb()."""
    layers = (under or {}).get("layers") or []
    assert (under or {}).get("opaque") is True and layers, "no opaque background under it: %r" % (under,)
    assert all((ly.get("img") or "none") == "none" for ly in layers), "a background image in its layers: %r" % (layers,)
    base = _rgba(layers[-1].get("bg"))
    assert base[3] == 1 and float(layers[-1].get("op")) == 1 and float(under.get("above")) == 1, \
        "an opacity on or above its opaque background: %r" % (under,)
    inner = layers[:-1]

    def paint(j, below):
        inside = _over(_rgba(inner[j].get("bg")), below)
        content = paint(j - 1, inside) if j else (_over(fg, inside) if fg else inside)
        op = float(inner[j].get("op"))
        return tuple(below[i] + op * (content[i] - below[i]) for i in range(3)) + (1.0,)
    if not inner:
        return _over(fg, base) if fg else base
    return paint(len(inner) - 1, base)


def _row_problems(engine, contrast):
    """Every button in the card's row of moved actions, as the page lists them, hovered: each label reads TEXT_FLOOR or more on
    the fill its button wears hovered, in the dark and the light theme (romp-manager's ruling at the launch of PR 976's round 3,
    item 1: the whole row, not a list of labels). The list is the page's own, so a button added to the row later is read with no
    edit here; the three the row holds today (MOVED) must be among those read, so a read that lists fewer is a red, not a pass.
    Each button must be enabled and hold :hover with the pointer on it (the read is of a hover), and show a label."""
    out = []
    for name, theme in THEMES:
        where = "%s row of moved actions hovered, %s theme (%s)" % (engine, name, theme)
        rw = (contrast.get(name) or {}).get("row")
        if not rw:
            out.append("%s: not read" % where)
            continue
        buttons = rw.get("buttons") or []
        acts = [b.get("act") for b in buttons if b]
        if rw.get("ended") is not True or rw.get("count") != len(buttons) or not set(MOVED) <= set(acts):
            out.append("%s: the premise (an opening over the lab's reading whose ask has ended, every button the row holds read, "
                       "the row's %s among them): ended %r, %r of %r read, acts %r" % (
                           where, list(MOVED), rw.get("ended"), len(buttons), rw.get("count"), acts))
        for b in buttons:
            if not b:
                out.append("%s: a button the page listed is gone at its read" % where)
                continue
            bw = "%s, %r (%s)" % (where, b.get("title"), b.get("act"))
            if b.get("hovered") is not True or b.get("disabled") is not False:
                out.append("%s: the premise (enabled, the pointer on it holding :hover): hovered %r, disabled %r" % (
                    bw, b.get("hovered"), b.get("disabled")))
                continue
            if not b.get("labels"):
                out.append("%s: no label seen" % bw)
            for lb in b.get("labels") or []:
                try:
                    px, fill = _through(_rgba(lb.get("colour")), lb.get("under")), _through(None, lb.get("under"))
                    ratio = _contrast(px, fill)
                    if ratio < TEXT_FLOOR:
                        out.append("%s: its label %r reads %.2f:1 (%s, %s) on the fill its button wears hovered (%s), under %g:1" % (
                            bw, lb.get("text"), ratio, lb.get("colour"), _hex(px), _hex(fill), TEXT_FLOOR))
                except (AssertionError, TypeError, ValueError) as e:
                    out.append("%s: its label %r is unmeasured: %s" % (bw, lb.get("text"), e))
    return out


class MtabsFit(unittest.TestCase):
    """One lab kernel for every leg (setUpClass); each leg is one driver run in one engine."""
    maxDiff = None

    @classmethod
    def setUpClass(cls):
        if not os.path.isdir(os.path.join(EXT, "node_modules", "playwright")):
            raise unittest.SkipTest("extension deps absent (npm ci not run here): the served leg needs them")
        cls.lab = tempfile.mkdtemp(prefix="mtabs-fit-")
        cls.addClassCleanup(lab_ports.release, cls.lab)   # runs on a failed setUpClass too, which skips tearDownClass
        dist = os.path.join(cls.lab, "dist")
        lab_dist.copy_dist(dist)   # the checkout's ONE build of the bundles, copied under its lock (tests/lab_dist.py)
        os.makedirs(os.path.join(cls.lab, "xdg", "romp"), exist_ok=True)
        # an API-key machine's usage reading (spend windows, zeros): the Usage modal opens only over a reading
        Path(cls.lab, "xdg", "romp", "usage.json").write_text(json.dumps({"apiKey": True}))
        cls.port, cls.token = lab_ports.reserve(cls.lab), "testtok-mtabsfit"
        cls.env = _lab.kernel_env(cls.lab, os.path.join(cls.lab, "claude"), dist, cls.port, cls.token)
        cls.klog = os.path.join(cls.lab, "kernel.log")
        cls.kernel = subprocess.Popen([os.path.join(BIN, "romp-kernel")], stdout=open(cls.klog, "w"),
                                      stderr=subprocess.STDOUT, env=cls.env)
        why = lab_ports.wait_owned(cls.kernel, cls.env)
        if why:
            cls.kernel.kill()
            cls.kernel.wait()
            raise unittest.SkipTest("hermetic kernel never served /healthz here: " + why)

    @classmethod
    def tearDownClass(cls):
        if getattr(cls, "kernel", None):
            cls.kernel.kill()
            cls.kernel.wait()
        lab_ports.release(getattr(cls, "lab", ""))
        shutil.rmtree(getattr(cls, "lab", ""), ignore_errors=True)

    def _drive(self, engine):
        declared = os.environ.get("ROMP_SERVED_TESTS_ENGINES", "")
        if engine != "chromium" and declared and engine not in [e.strip() for e in declared.split(",")]:
            self.skipTest("optional: this runner declares no %s (ROMP_SERVED_TESTS_ENGINES=%s)" % (engine, declared))
        cfg = {"engine": engine, "url": "http://127.0.0.1:%d/?token=%s" % (self.port, self.token),
               "healthz": "http://127.0.0.1:%d/healthz" % self.port, "settleMs": 100,
               "viewports": [list(v) for v in PORTRAIT + LANDSCAPE], "dynamicViewport": list(DYNAMIC),
               "actsViewport": list(ACTS), "moved": list(MOVED), "restartRefusal": RESTART_REFUSAL,
               "tunnels": TUNNELS, "tunnels2": TUNNELS2, "tunnelsDrop": TUNNELS_DROP,
               "tunnelsAttach": TUNNELS_ATTACH, "tunnelsNone": TUNNELS_NONE, "themes": [list(t) for t in THEMES],
               "desktopViewport": list(DESKTOP), "railViewports": [list(v) for v in RAIL], "wideViewport": list(WIDE),
               "errorStatus": ERROR_STATUS, "hangMs": HANG_MS, "hangWaitMs": HANG_WAIT_MS, "raceMs": RACE_MS,
               "heightWidths": list(HEIGHT_WIDTHS),
               "result": os.path.join(self.lab, "result-%s.json" % engine)}
        cfg_path = os.path.join(self.lab, "cfg-%s.json" % engine)
        Path(cfg_path).write_text(json.dumps(cfg))
        try:
            p = subprocess.run(["node", DRIVER], capture_output=True, text=True, timeout=420,
                               env=dict(os.environ, EXT_PKG=os.path.join(EXT, "package.json"), CFG=cfg_path))
        except subprocess.TimeoutExpired as e:
            so = e.stdout if isinstance(e.stdout, str) else (e.stdout or b"").decode()
            self.fail("driver timed out; partial output:\n%s" % so[-3000:])
        if p.returncode == 3:
            if engine == "chromium":
                self.skipTest("no playwright chromium on this box: the served leg needs one (CI installs it)")
            self.skipTest("optional: no playwright %s on this machine: %s" % (engine, p.stderr.strip()[-300:]))
        self.assertEqual(p.returncode, 0, "driver failed:\n" + p.stdout[-3000:] + p.stderr[-3000:])
        line = next((ln for ln in p.stdout.splitlines() if ln.startswith("RESULT-FILE:")), None)
        self.assertIsNotNone(line, "driver printed no result:\n" + p.stdout[-3000:] + p.stderr[-3000:])
        self.assertEqual(line[len("RESULT-FILE:"):], cfg["result"], "the driver wrote the file it was given")
        raw = Path(cfg["result"]).read_text()
        if DUMP:
            os.makedirs(DUMP, exist_ok=True)
            Path(DUMP, engine + ".json").write_text(raw)
        r = json.loads(raw)
        self.assertNotIn("died", r, "driver aborted early: %r (kernel log tail: %s)" % (r.get("died"), Path(self.klog).read_text()[-800:]))
        self.assertEqual(r.get("errors"), [], "page errors")
        return r

    def _leg(self, engine):
        r = self._drive(engine)
        problems, phones = [], 0
        for name in ("default", "files"):
            rows = r["sets"][name]
            self.assertEqual([tuple(x["vp"]) for x in rows], list(PORTRAIT + LANDSCAPE), engine + ": every phone was read")
            for row in rows:
                where = "%s %s %dx%d" % (engine, name, row["vp"][0], row["vp"][1])
                if not row["mobile"]:
                    # only a landscape phone wider than the query's 820px, in an engine whose emulation gives no coarse pointer
                    self.assertGreater(row["vw"], 820, where + ": the phone layout is off only past 820px: %r" % (row,))
                    self.assertEqual(row["display"], "none", where + ": no phone layout, no bar")
                    continue
                phones += 1
                self.assertTrue(row["fonts"], where + ": the webfont is in, so the labels have their served widths")
                self.assertEqual((row["bell"] or {}).get("hidden"), False, where + ": the bell shows (the shell reveals it on every page): %r" % (row["bell"],))
                keys = [c["key"] for c in row["controls"] if not c["tab"]]
                if keys != list(BAR_ACTS):
                    problems.append("%s: the bar's actions are %s, not %s (Usage, Remote kernels and Restart kernel live in the settings card)" % (where, keys, list(BAR_ACTS)))
                self.assertEqual(len([c for c in row["controls"] if c["tab"]]), 6 if name == "files" else 5, where + ": the tab set")
                problems += _problems(where, row)
                if row["vp"][1] > row["vp"][0]:
                    if row["vp"][0] in ONE_ROW[name]:
                        problems += _shape(where + " (one row owed)", row, "one")
                    if row["vp"][0] == FALLBACK.get(name):
                        problems += _shape(where + " (the fallback owed)", row, "two")
        self.assertGreaterEqual(phones, 2 * len(PORTRAIT), engine + ": every portrait phone was read on the phone layout")
        d = r["dynamic"]
        where = "%s files turned on at %dx%d" % (engine, d["vp"][0], d["vp"][1])
        # the leg's premises, listed with the rest (a red run names every failing reading, not the first)
        if d["before"]["natural"] > d["before"]["vw"] + EPS:
            problems.append("%s: the default set does not fit one row here (the leg's premise): natural %g" % (where, d["before"]["natural"]))
        if d["after"]["natural"] <= d["after"]["vw"] + EPS:
            problems.append("%s: the Files set fits one row here (the leg's premise): natural %g" % (where, d["after"]["natural"]))
        problems += _problems(where + " (before)", d["before"])
        problems += _problems(where, d["after"])
        problems += _acts_problems(engine, r["acts"])
        problems += _states_problems(engine, r["acts"])
        problems += _no_reading_problems(engine, r.get("noReading") or {"vp": list(ACTS)})
        problems += _unpulled_problems(engine, r.get("unpulled") or {"vp": list(ACTS)})
        problems += _failed_problems(engine, r.get("failedReads") or {"vp": list(ACTS)})
        problems += _skew_problems(engine, r.get("skew") or {"vp": list(ACTS)})
        problems += _follow_problems(engine, r.get("follow") or {"vp": list(ACTS), "wide": list(WIDE)})
        problems += _contrast_problems(engine, r.get("contrast") or {})
        problems += _row_problems(engine, r.get("contrast") or {})
        problems += _height_problems(engine, r.get("contrast") or {})
        self.assertEqual([tuple(x["vp"]) for x in r["rail"]], list(RAIL), engine + ": every rail width was read")
        problems += _rail_problems(engine, r["rail"])
        self.assertEqual(r["desktop"]["display"], "none", engine + ": the desktop shows no phone bar: %r" % (r["desktop"],))
        self.assertIs(r["desktop"]["mobile"], False, engine + ": the desktop window is not the phone layout: %r" % (r["desktop"],))
        self.assertEqual(problems, [], "\n".join(problems))

    def test_chromium_every_control_on_screen_at_every_phone_width(self):
        self._leg("chromium")

    # WebKit is Safari's engine and Firefox the third; `optional:` skips where the browser is absent (CI installs Chromium alone)
    def test_webkit_every_control_on_screen_at_every_phone_width(self):
        self._leg("webkit")

    def test_firefox_every_control_on_screen_at_every_phone_width(self):
        self._leg("firefox")


if __name__ == "__main__":
    unittest.main()

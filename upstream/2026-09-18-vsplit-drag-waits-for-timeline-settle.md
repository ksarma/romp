---
title: The vertical-split drag test waits for the timeline band to settle before it measures
status: approved
where: tests/test_chat_vsplit_served.py (the pointer driver: the settled() wait on the band, test_0 pane-rect hold, VSplitDragLateTimeline; and the failing-before reproduction BARS_HOLD_JS, BARS_RELEASE_JS, _bars_held_past_the_zone and VSplitDragBarsHeldPastTheZone)
added: 2026-09-18
pr:
tier: docs
offered:
closed:
---
Upstream copy has the same race: the timeline band collapses from its 250 px loader to two lanes when the bars land, the shell auto-fits the band, and a drag begun before that measures a drop zone the collapse moves (533 to 686 px pane). The driver now waits for the band settle event and names the step and the measured heights when it times out. Tests only.

**Addendum 2026-09-19: the failing-before reproduction this entry lacked.** When the
settle wait landed, the only case exercising it (VSplitDragLateTimeline) said in its own
docstring that it does NOT reproduce the CI shape and that on a fast box the drop lands
with or without the wait, so the change shipped with no test that discriminates it. The
addendum supplies one. It holds the timeline's bars frames on the wire until the driver
has measured the drop zone, releases them there, and waits for the band's settle event
before the pointer moves: no sleep, no retry, no threshold, the release keyed on the
measure and the drag on the settle. Without the wait the zone is measured at the
loader-height pane (533), the released bars collapse the band, the pane grows to 686, the
zone pinned to its bottom moves out from under the pointer and the drop misses, which is
the 2026-09-18 CI shape exactly. Measured 12 red of 12 at the pre-fix parent and 12 green
of 12 at the fix, and re-verified independently by romp-manager on current main (6 passed
at the fix, 5 failed at the parent). One coupling is stated in the class docstring: with
the bars held, the settle at the fix comes from the timeline view's own loader backstop,
so the reproduction depends on that backstop being shorter than the driver's settle wait,
and it fails loudly with the wait's named message if that ceases to hold.

2026-09-19: verified on the project's own base ea3c82725 (its copy of the test byte-identical to main's): the module at -n 4
under a busy-loop load, nine runs each way: as-is 1 red with the CI shape (the driver dies on the 20 s split wait; pane 533 px
at the zone measure, 686 at the ghost), with the settle wait 0 red; the VSplitDragBarsHeldPastTheZone case appended to their
file: 5 failed without the wait, 5 passed with it, alone and under load, same geometry. Placement note for the port: PR 771's
27-line settle block does not apply by context because the project's pointer driver finds and measures the tab in-page; it
goes after the bottom tab is found and draggable and immediately before the pane measure (out.pane), with
out.settled = await settled() as the last line before it.


2026-09-19: approved for offer by the user (his answer at 07:02Z on todo ut-1acd8aae, the consolidated ask that named this entry with the two other test fixes outside the 2026-09-18 plan's batches: yes). Offered on its own branch from the project's tip, not stacked, since no open offer touches this file; publish waits for a slot under the open-offer throttle.

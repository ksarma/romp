---
title: Two innerHeight reads in the phone shell script take the layout viewport's height and read the visual viewport's in WebKit under a standing pinch (the keyboard-open test on the tab bar's fallback re-bind road; the bell popover's bottom): recorded and to be reported at the source, not overridden; whether a pinch is reachable on iOS Safari under the page's user-scalable=no meta is the OPEN question, unverified on device
status: follow-up
where: `kernel/kernel.py` (the shell script: the keyboard-open test `innerHeight - visualViewport.height * scale > 120` read only through the tab bar re-bind fallback; the bell popover placement `bottom = innerHeight - rect.top + 6` on a fixed box, run at every bell tap)
added: 2026-09-20
pr:
tier: docs
offered:
closed:
---
Both lines are the project's (present at the merge base and on the project's main), so the fork does not patch them: a fix at the source reaches every fold, and an override would be permanent cost for a benefit nobody has confirmed reachable. Evidence: WebKit's LocalDOMWindow::innerHeight returns the unobscured content rect's height, which on iOS is the delegated unobscured size WebPage::updateVisibleContentRects sets from the visual viewport (WebKit source read 2026-09-20); Chromium keeps innerHeight at the layout viewport under a page scale of 2 (an iPhone 14 descriptor: visualViewport.height 422, innerHeight 844, documentElement.clientHeight 844). Headless Linux WebKit refuses a page scale above 1, so the WebKit half rests on the source alone; the on-device read of innerHeight and documentElement.clientHeight under a pinch is the only real-engine confirmation and is missing. The keyboard-gap change (fork PR 858) reads documentElement.clientHeight on its own roads and states the same premise once in its fit() comment. The signal that closes this entry: a device read showing a pinch reachable under the meta, at which point the fork's override becomes worth its cost, or a project change at the two lines.

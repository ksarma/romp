---
title: The phone shell leaves no empty band between the composer and the keyboard: the visual viewport's pan is published and the tab bar's reservation follows the bar's own box
status: candidate
where: kernel/kernel.py (_LANDING_MOBILE_JS fit and kbOpen; the mobile media block's body rule); tests/test_kernel_mobile.py; tests/test_shell_viewport_fit.py; tests/test_keyboard_gap_served.py; tests/keyboard_gap_browser.mjs
added: 2026-09-19
pr: 858
tier: fix
offered:
closed:
---
iPhone, the installed app: with the keyboard up the composer sat about 80 CSS px above the keyboard's accessory bar over bare page background. Two independent causes closed. The pan: iOS reveals a focused input by moving the visual viewport down the layout viewport (offsetTop > 0) with no document scroll to undo, and nothing read offsetTop; fit() publishes --app-top = round(vv.offsetTop) under the coarse-pointer guard and the height's validity guard (held under a pinch, clamped at use to the layout viewport less the height the same run publishes, never lowered in place) and the mobile block fixes the body and the picker's lift at it, so both cover exactly the visible band. The reservation: kbOpen read the keyboard only from the visual viewport being far shorter than the layout viewport, missing a keyboard that shrinks the layout viewport too while the fixed bar is outside the visible band; the strip is now the part of the bar's own box inside the band the shell published (--app-top to --app-top + --app-h) whenever the box can be read (upstream's reading stands only where it cannot): nothing for a bar below the band, the whole height for a bar wholly inside, the overlap for a pan that brings it partway in, at any zoom, so the bar never covers the composer and no strip stands over bar the keyboard hides. Pinned by the node fit harness, source pins, and a served phone leg (Chromium and WebKit, iPhone 14 descriptor, a fake visualViewport installed before the shell script parses) whose gap assertion is red on the base tree by 83 px.

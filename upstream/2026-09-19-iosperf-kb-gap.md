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
iPhone, the installed app: with the keyboard up the composer sat about 80 CSS px above the keyboard's accessory bar over bare page background. Two independent causes closed. The pan: iOS reveals a focused input by moving the visual viewport down the layout viewport (offsetTop > 0) with no document scroll to undo, and nothing read offsetTop; fit() publishes --app-top = round(vv.offsetTop) under the coarse-pointer guard (held under a pinch) and the mobile block fixes the body at it, so the body covers exactly the visible band. The reservation: kbOpen read the keyboard only from the visual viewport being far shorter than the layout viewport, missing a keyboard that shrinks the layout viewport too while the fixed bar is outside the visible band; it now reads the bar's own box against the band's bottom edge whenever the box can be read (upstream's reading stands only where it cannot, and under a pinch), which keeps the strip for any bar inside the visible band, one an engine shows above the keyboard (Android Chrome under resizes-content) or one the pan brings into the band, so the bar never covers the composer. Pinned by the node fit harness, source pins, and a served phone leg (Chromium and WebKit, iPhone 14 descriptor, a fake visualViewport installed before the shell script parses) whose gap assertion is red on the base tree by 83 px.

// The context/usage pressure fallback — ONE threshold pair and one three-state palette for every
// gauge (2026-08-27). Before this, the ctx gauges said 60/85 in three copies while the usage bars
// said 70/90 in two more: the same fullness wore different alarms on different surfaces. The
// kernel normally ships the continuous tone (kernel/colormap.py context_rgb — calm teal filling
// up, amber past CTX_WARN, red past CTX_DANGER); these values fire only when an older kernel
// didn't ship a color, so the fallback is the simple three-state form of the same semantics.
// kernel/colormap.py owns the canonical pair; tests/test_kernel_context_colormap.py pins it there
// and ctx-threshold parity is grep-pinned against this file (the timeline, plain JS in a foreign
// host, inlines the same numbers — see ui/romp-timeline-view.js).
export const CTX_WARN = 70;
export const CTX_DANGER = 88;
const CALM = "#5196B8";     // tone_rgb("context", 0) — the calm end of the teal tone
const WARN = "#d7a23a";     // --warn
const DANGER = "#c0392b";   // --err

export function ctxFallbackColor(pct: number): string {
  return pct >= CTX_DANGER ? DANGER : pct >= CTX_WARN ? WARN : CALM;
}

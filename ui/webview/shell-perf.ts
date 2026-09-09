// The dashboard SHELL's performance collector (2026-09-09). The shell is the top-level window that frames the
// panes; it receives no frames of its own and has no bundle beyond the tiny ones the landing page loads
// (age-color-global.ts, palette-main.ts), so it recorded nothing. But Chromium delivers an iframe's
// long-animation-frame entries to the TOP-LEVEL window only: when the Files pane's viewer blocked the main
// thread for about 20 s during a divider drag, every pane's minute row arrived late and none carried a long
// frame, while the shell, had it been listening, would have seen every one with the pane script it ran
// (`files.js:<fn>@<pos>`). This bundle installs the same collector every pane runs (ui/webview/perf-telemetry.ts)
// under app "shell", with no frame brackets at all: its minute row is the long frames the shell observed,
// heap and DOM, posted through the shell's own kernel socket (window.__rompShellSend, kernel.py shellWS) on
// the same clientDiag channel the panes use, so `romp perf client` shows it as one more pane. The keys in
// the row are scrubbed as every pane's are (perf-telemetry.ts scriptKey, sanitizeInvoker): a script URL to
// its basename with no query, an inline shell script as `page:`, an invoker with no element id or URL.
//
// The shell socket redials on a close (shellWS), and __rompShellSend answers false while it is not open. A
// row it refuses is HELD, at most HELD_MAX of them (the pane shim caps its own queued breadcrumbs the same
// way: DIAG_QUEUE_MAX), and the held rows go ahead of the next row that finds the socket open. No timer of
// its own: the collector's minute flush is the retry, and one late row beats a lost one.
//
// Loaded by _landing() (kernel.py) as its own dist entry (esbuild.js); the collector never throws into the
// page, and a browser without performance.now or PerformanceObserver gets nothing (installPerfTelemetry
// returns null, the observer kind is "none").
import { installPerfTelemetry, type PerfPost, type RompPerf } from "./perf-telemetry";

export const SHELL_APP = "shell";
export const HELD_MAX = 20;

type ShellSend = (m: Record<string, unknown>) => boolean;

/** The shell's clientDiag transport: window.__rompShellSend, read at call time (the socket script runs after
 *  the bundles), with the held queue described above. Exported for the test; the page runs installShellPerf(). */
export function shellPost(send: () => ShellSend | undefined): PerfPost {
  const held: Record<string, unknown>[] = [];
  return (m) => {
    const s = send();
    if (typeof s !== "function") { hold(m); return; }
    while (held.length) {
      if (!s(held[0])) { hold(m); return; }   // still closed: keep the order, add this one
      held.shift();
    }
    if (!s(m)) hold(m);
  };
  function hold(m: Record<string, unknown>): void {
    if (held.length >= HELD_MAX) held.shift();   // the oldest goes: the newest minute is the one worth having
    held.push(m);
  }
}

/** Install the shell's collector on this window; null where nothing can be measured. */
export function installShellPerf(): RompPerf | null {
  const w: any = typeof window !== "undefined" ? window : null;
  if (!w) return null;
  return installPerfTelemetry(SHELL_APP, { post: shellPost(() => w.__rompShellSend) });
}

installShellPerf();

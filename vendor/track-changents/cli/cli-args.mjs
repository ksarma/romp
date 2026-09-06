'use strict';

// Shared option parser for the track-* CLIs. Every flag these CLIs accept
// takes a value, and the values are NOTE CONTENT — which can legitimately
// begin with dashes (YAML frontmatter "---", a bullet "- item"). The parser
// the CLIs used to inline treated any next-argv starting with "--" as a new
// flag, so `--new "$(printf -- '---\nkey: v')"` silently became --new ""
// and the engine replaced the --old span with EMPTY: rc 0, "applied", file
// truncated. Silent data loss (zeroed a stage note three times on
// 2026-08-19) — hence:
//
//  * a flag mid-argv ALWAYS consumes the next element as its value, dashes
//    or not (there are no boolean flags to protect);
//  * `--key=value` equals-form works, so values can also be attached;
//  * a flag with NOTHING after it stays UNSET (callers then fail loudly
//    with their "--x is required" checks) — it must never read as an
//    explicit empty string, because for --new an empty string means
//    "delete the span", and a trailing typo must not delete anything.
export function parseArgs(argv) {
  const out = {};
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (typeof a !== 'string' || !a.startsWith('--') || a === '--') continue;
    const eq = a.indexOf('=');
    if (eq > 2) { out[a.slice(2, eq)] = a.slice(eq + 1); continue; }
    const key = a.slice(2);
    const next = argv[i + 1];
    if (next === undefined) continue; // trailing flag: leave unset, caller errors
    out[key] = next;
    i++;
  }
  return out;
}

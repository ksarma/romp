'use strict';
// tests/manager-ports.js: loopback ports for the manager node tests, one disjoint block per file.
//
// `node --test tests/manager-*.test.js` runs the FILES concurrently, and several of them start a real
// bin/romp-manager on a port they picked. Until 2026-09-18 each file picked with listen-on-zero: bind
// port 0, read the number the operating system chose, close the socket, hand the number to the child.
// Between that close and the child's own bind the port is free again, for the milliseconds the spawn
// takes, and a second file's helper running at the same time can be handed the very same number,
// because the operating system picks from one pool for the whole machine and a released port is a
// candidate at once. In one sweep two cases failed together: manager-down.test.js's SIGKILL-after-the-grace case and
// manager-token.test.js's tokenless-POST case had been handed one port; the tokenless POST reached the
// other file's manager (its log carried the refusal line), and the second start answered "a manager is
// already running on :<port>". A rerun was clean, as a race of milliseconds is. The earlier fix in
// those files, fresh ports instead of literals, addressed a different collision (two suites sharing a
// literal control port) and left this one open: a free port is free for everybody, and the window
// between the probe's close and the child's bind is exactly where another file's probe runs.
//
// The fix is a partition: every manager test file owns a block of ports nobody else's helper can hand
// out, so two files cannot be given the same number however their probes interleave. The probe then
// runs INSIDE the block, binding the candidate itself (never port 0) and walking on EADDRINUSE, so a
// port a foreign process or an earlier case's manager still holds is skipped; a block with nothing left
// fails loudly. Within a process a returned port is never returned again (`used`): a file's cases run
// in sequence, and the manager of the last case may still be leaving its port during its exit grace.
// The walk starts at a random offset inside the block and wraps at its top, so two processes running
// the SAME file at once (two checkouts on one box) do not begin at the same candidate. That case keeps
// the window, narrowed rather than closed: the block separates the files of one run, which is the
// collision that happened; a shared machine's runs are kept apart by the offset and the probe alone.
//
// The band: 12000-17631, eleven blocks of 512, above the privileged ports and below Linux's ephemeral
// range (32768-60999, read from /proc/sys/net/ipv4/ip_local_port_range; macOS starts at 49152), so an
// outgoing connection is never handed one of these as its SOURCE port between the probe and the bind.
// It also sits under every band another suite on the same machine draws from: the bats helper's
// 20000-24999, the postal bus's 25302, the postal tests' 27200-28300 and the kernel's 29855 (all in
// tests/free-port.bash's header), and the postal port pytest derives from its pid in 20000-39999
// (tests/test_chat_pages.py, tests/test_judge_serve.py).
//
// The table is EXPLICIT so it is collision-free by construction: a file not in it is refused with the
// line to add, and tests/manager-ports.test.js pins that the blocks are pairwise disjoint, sit in the
// band, and match the tests/manager-*.test.js files on disk exactly (an entry without a file rots the
// table too). Callers pass `__filename`: `freePort(__filename)` for one port, `freePorts(__filename, n)`
// for several.
const crypto = require('node:crypto');
const fs = require('node:fs');
const net = require('node:net');
const path = require('node:path');

const RANGES = {
  'manager-down.test.js': [12000, 12511],
  'manager-drain.test.js': [12512, 13023],
  'manager-exit-attribution.test.js': [13024, 13535],
  'manager-fold.test.js': [13536, 14047],
  'manager-op-env.test.js': [14048, 14559],
  'manager-ports.test.js': [14560, 15071],
  'manager-quiet-window-audit.test.js': [15072, 15583],
  'manager-registry.test.js': [15584, 16095],
  'manager-restart.test.js': [16096, 16607],
  'manager-stale-consult.test.js': [16608, 17119],
  'manager-token.test.js': [17120, 17631],
};

// The low end of the band the operating system hands out to outgoing connections: the sysctl where
// Linux exposes it, the documented Linux default elsewhere (macOS's 49152 is higher, so the default is
// the stricter of the two).
function ephemeralLow() {
  try {
    const low = Number(fs.readFileSync('/proc/sys/net/ipv4/ip_local_port_range', 'utf8').trim().split(/\s+/)[0]);
    if (Number.isInteger(low) && low > 0) return low;
  } catch (e) { /* not Linux, or unreadable */ }
  return 32768;
}

const used = new Set();     // every port this process has handed out, by any file
const starts = new Map();   // per file, the offset this process walks from

function rangeFor(file) {
  const base = path.basename(file);
  const r = RANGES[base];
  if (!r) throw new Error(`manager-ports: ${base} has no port block; add a disjoint [lo, hi] for it to RANGES in tests/manager-ports.js`);
  return r;
}

// Bind the candidate itself on the loopback the manager binds: true when it took, false when another
// process holds it (EADDRINUSE) or the box refuses it (EACCES); any other error is the caller's.
function bindable(port) {
  return new Promise((resolve, reject) => {
    const s = net.createServer();
    s.once('error', (e) => (e.code === 'EADDRINUSE' || e.code === 'EACCES' ? resolve(false) : reject(e)));
    s.listen(port, '127.0.0.1', () => s.close(() => resolve(true)));
  });
}

// The first port in [lo, hi], walking up from `start` and wrapping past `hi` to `lo`, that is neither in
// `taken` nor held by anyone; marks it taken.
async function nextFree(lo, hi, taken, start = lo) {
  const size = hi - lo + 1;
  for (let i = 0; i < size; i++) {
    const p = lo + ((start - lo + i) % size);
    if (taken.has(p)) continue;
    if (await bindable(p)) { taken.add(p); return p; }
  }
  throw new Error(`manager-ports: no free port left in ${lo}-${hi} (${taken.size} handed out in this process, the rest held by other processes)`);
}

async function freePort(file) {
  const [lo, hi] = rangeFor(file);
  const base = path.basename(file);
  if (!starts.has(base)) starts.set(base, lo + crypto.randomInt(hi - lo + 1));
  return nextFree(lo, hi, used, starts.get(base));
}

async function freePorts(file, n) {
  const out = [];
  for (let i = 0; i < n; i++) out.push(await freePort(file));   // in sequence: `used` is what keeps them distinct
  return out;
}

module.exports = { RANGES, ephemeralLow, freePort, freePorts, nextFree };

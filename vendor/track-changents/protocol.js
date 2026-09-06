'use strict';

// The sidecar PROTOCOL in one importable module: every constant and
// naming rule a host must agree on to share `.trackchanges/` with the
// other tools. The store layer here (`store-io.mjs`) builds on these;
// a host that reimplements storage over its own fs layer (an Obsidian
// vault adapter, say) should import THIS rather than retyping the
// values — the copies drifting is how shared files get corrupted.
// Dependency-free and browser-safe (no fs, no crypto at module scope).

const STORE_DIR = '.trackchanges';
const STORE_VERSION = 3;           // gate: refuse to touch a store with a higher v
const CONFIG_NAME = 'config.json';
const CONFIG_VERSION = 2;

// One store per tracked file: <root>/.trackchanges/<encoded relpath>.json
function storeFileName(relPath) {
  return encodeURIComponent(String(relPath)) + '.json';
}

// A superseded PARK: a store displaced by a foreign write is renamed
// aside (never deleted) so nothing is silently lost. The bare form is
// the most recent park; earlier parks carry their timestamp.
function parkName(storeName, ts) {
  return ts == null ? `${storeName}.superseded` : `${storeName}.superseded-${ts}`;
}
function isParkName(name) {
  return /\.superseded(?:-\d+)?$/.test(String(name));
}

// The store's freshness check: sha256 of the CURRENT file text plus its
// length. Node-only helper (lazy require keeps the module browser-safe);
// browser hosts compute the same shape with their own sha256.
function fingerprintOf(currentText) {
  const crypto = require('node:crypto');
  const s = String(currentText);
  return { hash: crypto.createHash('sha256').update(s).digest('hex'), size: s.length };
}

module.exports = {
  STORE_DIR, STORE_VERSION, CONFIG_NAME, CONFIG_VERSION,
  storeFileName, parkName, isParkName, fingerprintOf,
};

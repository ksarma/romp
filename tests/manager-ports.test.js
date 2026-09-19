'use strict';
// tests/manager-ports.js, the per-file port blocks the manager node tests draw from (2026-09-18: two
// files running concurrently were handed one port by listen-on-zero; the header there has the story).
// Pinned here: the table is pairwise disjoint, inside the band, and matches the manager-*.test.js files
// on disk; the helper hands out only ports in the caller's block and never one twice; an unknown file
// is refused; a port somebody holds is skipped; the walk wraps at the block's top; an exhausted block
// fails loudly.
// Run from the repo root: node --test tests/manager-*.test.js
const { test } = require('node:test');
const assert = require('node:assert');
const fs = require('node:fs');
const net = require('node:net');
const path = require('node:path');
const { RANGES, ephemeralLow, freePort, freePorts, nextFree } = require(path.join(__dirname, 'manager-ports'));

const MINE = RANGES[path.basename(__filename)];

// Hold `port` on the loopback the helper probes; null when somebody else has it.
function hold(port) {
  const s = net.createServer();
  return new Promise((resolve) => { s.once('error', () => resolve(null)); s.listen(port, '127.0.0.1', () => resolve(s)); });
}
const release = (s) => new Promise((r) => s.close(r));

test('the table: every block is [lo, hi] with lo <= hi, above the privileged ports and below the ephemeral range, and no two blocks share a port', () => {
  const low = ephemeralLow();
  const entries = Object.entries(RANGES);
  for (const [name, r] of entries) {
    assert.ok(Array.isArray(r) && r.length === 2 && Number.isInteger(r[0]) && Number.isInteger(r[1]), `${name}: ${JSON.stringify(r)}`);
    const [lo, hi] = r;
    assert.ok(lo <= hi, `${name}: ${lo}-${hi} is empty`);
    assert.ok(lo > 1024, `${name}: ${lo} is a privileged port`);
    assert.ok(hi < low, `${name}: ${hi} reaches the box's ephemeral range (starts at ${low}); an outgoing connection could hold it`);
    assert.ok(hi < 32768, `${name}: ${hi} reaches the Linux default ephemeral range`);
  }
  for (let i = 0; i < entries.length; i++) {
    for (let j = i + 1; j < entries.length; j++) {
      const [a, [alo, ahi]] = entries[i], [b, [blo, bhi]] = entries[j];
      assert.ok(ahi < blo || bhi < alo, `${a} (${alo}-${ahi}) and ${b} (${blo}-${bhi}) overlap`);
    }
  }
});

test('the table names exactly the tests/manager-*.test.js files on disk: a new file must be given a block, and a block whose file is gone must go', () => {
  const onDisk = fs.readdirSync(__dirname).filter((f) => /^manager-.*\.test\.js$/.test(f)).sort();
  assert.deepEqual(Object.keys(RANGES).sort(), onDisk);
  assert.ok(onDisk.includes(path.basename(__filename)), 'this file draws from the table too');
});

test('freePort and freePorts hand out ports inside the caller\'s block only, each one once per process', async () => {
  const [lo, hi] = MINE;
  const got = [await freePort(__filename), ...(await freePorts(__filename, 5)), await freePort(__filename)];
  for (const p of got) assert.ok(Number.isInteger(p) && p >= lo && p <= hi, `${p} is outside ${lo}-${hi}`);
  assert.equal(new Set(got).size, got.length, `a port came back twice: ${got.join(' ')}`);
  const again = await freePorts(__filename, 3);
  for (const p of again) assert.ok(!got.includes(p), `${p} was handed out before`);
  assert.equal(new Set(again).size, 3);
});

test('a file with no block is refused, naming the file and the table', async () => {
  await assert.rejects(freePort(path.join(__dirname, 'manager-nonesuch.test.js')), /manager-nonesuch\.test\.js has no port block.*RANGES in tests\/manager-ports\.js/);
  await assert.rejects(freePorts('/elsewhere/other.test.js', 2), /other\.test\.js has no port block/);
});

test('a port somebody holds inside the block is skipped, not returned', async () => {
  const [lo, hi] = MINE, size = hi - lo + 1;
  const first = await freePort(__filename);
  // The walk is a ring from this process's offset, skipping what it handed out, so the next answer is
  // the first bindable port after `first` in ring order. Hold that one ourselves: the helper must step
  // over it.
  let holder = null, held = 0;
  for (let k = 1; k < size && !holder; k++) {
    held = lo + ((first - lo + k) % size);
    holder = await hold(held);
  }
  assert.ok(holder, `nothing after ${first} in ${lo}-${hi} could be bound for the test`);
  try {
    const next = await freePort(__filename);
    assert.notEqual(next, held, `the helper handed out ${held}, a port another socket holds`);
    assert.ok(next >= lo && next <= hi, `${next} is outside ${lo}-${hi}`);
  } finally {
    await release(holder);
  }
});

test('the walk wraps: a start near the top of the block continues from its bottom', async () => {
  const [lo, hi] = MINE;
  const taken = new Set([hi]);
  const holder = await hold(lo);
  try {
    const p = await nextFree(lo, hi, taken, hi);   // hi is taken, lo is held (by us, or by whoever had it): the answer is past both
    assert.ok(p > lo && p < hi, `from ${hi} with ${hi} taken and ${lo} held the walk should wrap past ${lo}: got ${p}`);
    assert.ok(taken.has(p), 'the answer is marked taken');
  } finally {
    if (holder) await release(holder);
  }
});

test('an exhausted block fails loudly with the range and the count handed out', async () => {
  const [lo] = MINE;
  const taken = new Set([lo, lo + 1, lo + 2]);
  await assert.rejects(nextFree(lo, lo + 2, taken), new RegExp(`no free port left in ${lo}-${lo + 2} \\(3 handed out`));
  const holder = net.createServer();
  const port = await new Promise((resolve) => holder.listen(0, '127.0.0.1', () => resolve(holder.address().port)));
  try {
    await assert.rejects(nextFree(port, port, new Set()), /no free port left/, 'a one-port range whose port is held is exhausted too');
  } finally {
    await release(holder);
  }
});

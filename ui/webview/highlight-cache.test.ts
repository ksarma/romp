// The fence highlight cache (highlight-cache.ts, 2026-09-06): the same (language, source) tokenizes once
// while its entry is held; an unlabeled fence still goes through auto-detection over every grammar (the
// detection is kept — only the repeat work goes); the cache is bounded by entries and by output size.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import { highlightHtml, newHighlightCache, CAP, BUDGET, MAX_RAW } from "./highlight-cache";

function stub() {
  const calls = { highlight: 0, auto: 0 };
  const hl = {
    getLanguage: (name: string) => (name === "python" || name === "bash" ? {} : undefined),
    highlight: (raw: string, o: { language: string }) => { calls.highlight++; return { value: `<${o.language}>${raw}</${o.language}>` }; },
    highlightAuto: (raw: string) => { calls.auto++; return { value: `<auto>${raw}</auto>` }; },
  };
  return { hl, calls };
}

test("the same fence twice tokenizes once; a labeled fence goes to its grammar, an unlabeled one to auto-detection", () => {
  const { hl, calls } = stub();
  const c = newHighlightCache();
  assert.equal(highlightHtml(hl, "python", "print(1)", c), "<python>print(1)</python>");
  assert.equal(highlightHtml(hl, "python", "print(1)", c), "<python>print(1)</python>");
  assert.deepEqual(calls, { highlight: 1, auto: 0 });
  assert.equal(highlightHtml(hl, undefined, "print(1)", c), "<auto>print(1)</auto>", "no label: auto-detected, and a separate entry from the labeled one");
  assert.equal(highlightHtml(hl, undefined, "print(1)", c), "<auto>print(1)</auto>");
  assert.deepEqual(calls, { highlight: 1, auto: 1 });
});

test("an unknown language is auto-detected and shares the unlabeled entry (both mean: no grammar named)", () => {
  const { hl, calls } = stub();
  const c = newHighlightCache();
  highlightHtml(hl, "klingon", "x = 1", c);
  highlightHtml(hl, undefined, "x = 1", c);
  assert.deepEqual(calls, { highlight: 0, auto: 1 });
});

test("a different source, or the same source in another language, is its own entry", () => {
  const { hl, calls } = stub();
  const c = newHighlightCache();
  highlightHtml(hl, "python", "a", c); highlightHtml(hl, "python", "b", c); highlightHtml(hl, "bash", "a", c);
  assert.deepEqual(calls, { highlight: 3, auto: 0 });
  assert.equal(c.map.size, 3);
});

test("bounded by entries: the oldest goes first, and a hit counts as newest", () => {
  const { hl, calls } = stub();
  const c = newHighlightCache();
  for (let i = 0; i < CAP; i++) highlightHtml(hl, "python", "line " + i, c);
  assert.equal(c.map.size, CAP);
  highlightHtml(hl, "python", "line 0", c);            // a hit: "line 0" is newest now
  highlightHtml(hl, "python", "one more", c);          // pushes out the oldest, which is "line 1"
  assert.equal(c.map.size, CAP);
  const before = calls.highlight;
  highlightHtml(hl, "python", "line 0", c);
  assert.equal(calls.highlight, before, "the refreshed entry survived");
  highlightHtml(hl, "python", "line 1", c);
  assert.equal(calls.highlight, before + 1, "the evicted entry tokenizes again");
});

test("bounded by output size, and a very large source is highlighted but never kept", () => {
  const { hl, calls } = stub();
  const c = newHighlightCache();
  const big = "x".repeat(Math.floor(BUDGET / 3) + 1);
  highlightHtml(hl, "python", big + "1", c); highlightHtml(hl, "python", big + "2", c); highlightHtml(hl, "python", big + "3", c);
  assert.ok(c.map.size < 3 && c.chars <= BUDGET + big.length + 40, "the budget evicted the oldest: " + c.map.size + " held, " + c.chars + " chars");
  const huge = "y".repeat(MAX_RAW + 1);
  const n = c.map.size;
  assert.equal(highlightHtml(hl, "python", huge, c), `<python>${huge}</python>`);
  assert.equal(c.map.size, n, "not kept");
  highlightHtml(hl, "python", huge, c);
  assert.equal(calls.highlight, 5, "…so it tokenizes each time");
});

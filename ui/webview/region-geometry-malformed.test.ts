// A region the sidecar holds in the wrong shape (plans/file-review.md, Slice 3; Security posture: the panel
// reads the sidecar as it is on disk). The host validates only what IT writes (validateTarget), store-io hands
// the comments through untouched, and cardModel words every comment — so one coordinate that was not a finite
// number (a hand edit; a foreign writer of the romp-only `target` field) threw `toFixed is not a function` out
// of fmt2 for every render of that file's panel: no cards, no error row, nothing said why. The geometry is
// total over what it is given now — an unreadable coordinate prints as "?" in its slot, on its own card — and
// isRegion is the guard a caller uses before placing or cropping. Synthetic values only.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import { isRegion, fmt2, regionDesc, UNREADABLE, type Region } from "./region-geometry";
import { cardModel, describeComment, type Store, type StoreComment } from "./file-comments-model";

const GOOD: Region = { x: 0.1, y: 0.2, w: 0.3, h: 0.4 };
// the finding's specimen: the four fractions as strings, which JSON keeps and the host would have refused
const STRINGS = { x: "0.1", y: "0.2", w: "0.3", h: "0.4" };

test("isRegion: an object whose x, y, w and h are all finite numbers — the shape the host writes — and nothing else", () => {
  assert.equal(isRegion(GOOD), true);
  assert.equal(isRegion({ x: 0, y: 0, w: 1, h: 1 }), true, "the whole picture");
  assert.equal(isRegion({ ...GOOD, extra: "kept" }), true, "an extra key is not a malformed region");
  assert.equal(isRegion(STRINGS), false, "numeric strings are not fractions: the host refuses them, so does the guard");
  assert.equal(isRegion({ x: 0.1, y: 0.2, w: 0.3 }), false, "a missing coordinate");
  assert.equal(isRegion({ x: 0.1, y: null, w: 0.3, h: 0.4 }), false, "a null coordinate");
  assert.equal(isRegion({ x: 0.1, y: NaN, w: 0.3, h: 0.4 }), false, "NaN");
  assert.equal(isRegion({ x: 0.1, y: 0.2, w: Infinity, h: 0.4 }), false, "an infinity");
  assert.equal(isRegion({}), false);
  assert.equal(isRegion(true), false, "a truthy non-object passes cardModel's `target.region` truth test and used to reach fmt2");
  assert.equal(isRegion("0.1, 0.2, 0.3, 0.4"), false);
  assert.equal(isRegion([0.1, 0.2, 0.3, 0.4]), false, "an array is not the {x, y, w, h} shape");
  assert.equal(isRegion(null), false);
  assert.equal(isRegion(undefined), false);
});

test("fmt2: two decimals for a finite number, the unreadable mark for anything else — never a throw", () => {
  assert.equal(fmt2(0.4), "0.40");
  assert.equal(fmt2(1), "1.00");
  assert.equal(UNREADABLE, "?");
  for (const bad of ["0.1", undefined, null, NaN, Infinity, -Infinity, {}, true, [0.1]]) {
    assert.equal(fmt2(bad), UNREADABLE, "not a finite number: " + String(bad));
  }
});

test("regionDesc: total over what the sidecar holds — each unreadable coordinate marked in its slot, the phrase still composing with its tails", () => {
  assert.equal(regionDesc(GOOD), "the region at 0.10, 0.20, 0.30, 0.40", "a well-formed region words as before");
  assert.equal(regionDesc(STRINGS), "the region at ?, ?, ?, ?", "the finding's specimen: strings throughout");
  assert.equal(regionDesc({ x: 0.1, y: null, w: 0.3, h: 0.4 }), "the region at 0.10, ?, 0.30, 0.40", "one bad coordinate: the others still read, so the person sees which");
  assert.equal(regionDesc({ x: 0.1, y: 0.2, w: 0.3 }), "the region at 0.10, 0.20, 0.30, ?", "a missing coordinate");
  assert.equal(regionDesc({ x: 0.1, y: 0.2, w: NaN, h: 0.4 }), "the region at 0.10, 0.20, ?, 0.40", "NaN never prints as NaN");
  assert.equal(regionDesc({}), "the region at ?, ?, ?, ?");
  assert.equal(regionDesc(true), "the region at ?, ?, ?, ?", "a truthy non-object");
  assert.equal(regionDesc("0.1, 0.2, 0.3, 0.4"), "the region at ?, ?, ?, ?", "a string is not read as coordinates");
  assert.equal(regionDesc(null), "the region at ?, ?, ?, ?");
  assert.equal(regionDesc(undefined), "the region at ?, ?, ?, ?");
  assert.equal(regionDesc(STRINGS, 2), "the region at ?, ?, ?, ? of page 2", "the PDF page tail still attaches");
  assert.equal(regionDesc({ x: 0.1, y: null, w: 0.3, h: 0.4 }, null), "the region at 0.10, ?, 0.30, 0.40");
});

// The failure the finding describes, at the function whose throw killed the panel: cardModel words every comment
// through describeComment → regionDesc → fmt2, and every render path (render, paintAll, paintRegions, sendParts)
// calls it — so one malformed region used to empty the panel for the whole file.
const at = (id: string, body: string, region: unknown): StoreComment => ({
  id, author: "you", ts: Number(id.split("-")[0]), body, replies: [], resolved: false,
  target: { kind: "image", region: region as Region, hash: "ab" },
});
const store = (comments: StoreComment[]): Store => ({ v: 3, path: "docs/a.png", suggestions: [], comments });

test("cardModel: a sidecar whose region coordinates are strings still yields a card per comment — the panel renders, and the other comments are untouched", () => {
  const good = at("1757145600000-0", "The y axis needs units.", GOOD);
  const bad = at("1757145600001-0", "Legend overlaps the plot.", STRINGS);
  let cards: ReturnType<typeof cardModel> = [];
  assert.doesNotThrow(() => { cards = cardModel(store([bad, good]), []); }, "this threw `v.toFixed is not a function` before the fix");
  assert.equal(cards.length, 2, "both comments have a card");
  const [c0, c1] = cards;
  assert.equal(c0.id, good.id, "oldest first: the well-formed comment");
  assert.equal(c0.kind, "region");
  assert.equal(c0.ref, "the region at 0.10, 0.20, 0.30, 0.40", "the well-formed comment reads as before");
  assert.equal(c1.id, bad.id);
  assert.equal(c1.body, bad.body, "the person's words survive the malformed target");
  assert.doesNotMatch(c1.ref, /NaN|undefined|null/, "no coerced garbage in the reference: " + c1.ref);
});

test("cardModel: every malformed shape a foreign writer could leave under target.region words without throwing", () => {
  const shapes: unknown[] = [STRINGS, { x: 0.1, y: null, w: 0.3, h: 0.4 }, { x: 0.1, y: 0.2, w: 0.3 }, {}, true, "0.1,0.2,0.3,0.4", [0.1, 0.2, 0.3, 0.4], 1];
  shapes.forEach((shape, i) => {
    const c = at("175714560000" + i + "-0", "Note " + i, shape);
    assert.doesNotThrow(() => cardModel(store([c]), []), "shape #" + i + ": " + JSON.stringify(shape));
    assert.doesNotThrow(() => describeComment(c, []), "describeComment on shape #" + i);
    assert.doesNotMatch(describeComment(c, []), /NaN|undefined/, "desc for shape #" + i);
  });
});

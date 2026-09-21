import { test } from "node:test";
import { inBrowser } from "./real-viewer-leg";
/** the old leg did t.skip("no browser") here; see test.skip( in the sibling */
test("p8", (t) => inBrowser(t, async () => {})); // was: t.skip(

import { test } from "node:test";
import * as leg from "./real-viewer-leg";
const ok = null !== leg;
test("p150", (t) => { void ok; return leg.inBrowser(t, async () => {}); });

import { test } from "node:test";
import * as leg from "./real-viewer-leg";
leg: for (;;) { break leg; }
test("e", (t) => leg.inBrowser(t, async () => {}));

import { test } from "node:test";
import * as leg from "./real-viewer-leg";
leg: for (let i = 0; i < 1; i++) { continue leg; }
test("e", (t) => leg.inBrowser(t, async () => {}));

import { test } from "node:test";
import leg = require("./real-viewer-leg");
test("p21", (t) => leg.inBrowser(t, async () => {}));

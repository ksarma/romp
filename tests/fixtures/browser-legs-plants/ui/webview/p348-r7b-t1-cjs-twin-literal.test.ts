import { test } from "node:test";
const leg = require("./real-viewer-leg.cjs");
test("p348", (t) => leg.inBrowser(t, async () => {}));

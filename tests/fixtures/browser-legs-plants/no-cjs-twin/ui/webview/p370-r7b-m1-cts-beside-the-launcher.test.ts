import { test } from "node:test";
const leg = require("./real-viewer-leg.cjs");
test("p370", (t) => leg.inBrowser(t, async () => {}));

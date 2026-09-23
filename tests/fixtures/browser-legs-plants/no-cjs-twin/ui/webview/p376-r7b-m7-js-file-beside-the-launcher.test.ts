import { test } from "node:test";
const leg = require("./real-viewer-leg.js");
test("p376", (t) => leg.inBrowser(t, async () => {}));

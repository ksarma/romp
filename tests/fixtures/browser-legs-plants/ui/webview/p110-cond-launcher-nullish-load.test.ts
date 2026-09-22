import { test } from "node:test";
const leg = require("./real-viewer-leg") ?? null;
test("p110", (t) => leg.inBrowser(t, async () => {}));

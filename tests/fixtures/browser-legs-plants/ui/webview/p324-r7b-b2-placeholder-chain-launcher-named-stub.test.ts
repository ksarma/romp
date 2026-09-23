import { test } from "node:test";
const { inBrowser } = require(process.env.LEG_DIR + "/real-viewer-leg-stub");
test("p324", (t) => inBrowser(t, async () => {}));

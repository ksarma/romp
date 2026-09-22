import { test } from "node:test";
import { createRequire } from "node:module";
const { inBrowser } = createRequire(__filename)("./real-viewer-leg");
test("p54", async (t) => { await inBrowser(t, async () => {}); });

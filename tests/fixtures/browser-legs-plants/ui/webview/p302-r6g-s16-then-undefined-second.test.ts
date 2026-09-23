import { test } from "node:test";
import { inBrowser } from "./real-viewer-leg";
test("p302", async (t) => { await inBrowser(t, async () => {}).then(undefined, () => {}); });

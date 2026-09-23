import { test } from "node:test";
import { inBrowser } from "./real-viewer-leg";
test("p298", async (t) => { await inBrowser(t, async () => {}).then(() => {}); });

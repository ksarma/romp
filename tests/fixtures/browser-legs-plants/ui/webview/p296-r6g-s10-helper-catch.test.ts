import { test } from "node:test";
import { safe } from "./catch-helper";
import { inBrowser } from "./real-viewer-leg";
test("p296", async (t) => { await inBrowser(t, async () => {}); await safe(t); });
